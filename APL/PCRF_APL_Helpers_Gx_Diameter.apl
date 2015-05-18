/*
 * Module:                 PCRF_APL_Helpers 
 *
 * Date Created:           2012
 *
 * Author:                 DigitalRoute
 *
 * Purpose:                Common PCRF Gx interface functions, specific to Gx diameter profile
 *
 * Dependencies:           None
 *
 * Issues:                 None                             
 *
 * Comments:               Gx diameter functionality is based on 3GPP TS 29.212 V11.6.0 (2012-09), Release 11
 *                         This APL may be modified to suport vendor specific Gx diameter application profile
 */

import ultra.Diameter.Base;
import ultra.PCRF.Rules;
import ultra.Policy_Templates.PCRF_PRF_Diameter_Gx_3GPP_rel11;
import ultra.Policy_Templates.PCRF_UFL_Internal;

import apl.Policy_Templates.PCRF_APL_Configuration;
import apl.Policy_Templates.PCRF_APL_Constants;


/*
 * Purpose:  Extract fields from CCR, if Missing mandatory fields then set error in CCA Result-Code
 *          
 * Assumes:  Nothing
 *
 * Effects:  Nothing
 *
 * Comments: 
 *
 */
boolean extractCCR(rc rc) {

    // Missing input
    if (rc == null || rc.rc == null || rc.rc.Request == null
    || !instanceOf(rc.rc.Request, CC_Request)) {
        debug("extractCCR() Invalid input: [" + rc + "]");
        return false;
    }
    
    // Internal Error code list
    rc.errorCodes = listCreate(int);

    // Input CCR
    CC_Request in = (CC_Request)rc.rc.Request;

    // Internal CCR
    rc.ccr = udrCreate(ccr);
    rc.ccr.Session_Id = in.Session_Id;
    rc.ccr.CC_Request_Type = in.CC_Request_Type;
    rc.ccr.CC_Request_Number = in.CC_Request_Number;
    rc.ccr.Auth_Application_Id = in.Auth_Application_Id;

    // Internal CCA
    rc.cca = udrCreate(cca);
    rc.cca.Session_Id = in.Session_Id;
    rc.cca.CC_Request_Type = in.CC_Request_Type;
    rc.cca.CC_Request_Number = in.CC_Request_Number;
    rc.cca.Auth_Application_Id = in.Auth_Application_Id;
    rc.cca.Result_Code = DIAMETER_SUCCESS;
    rc.cca.ruleDeactTimeMap = mapCreate(int, date);

    // Failed-AVP
    list<Base.AVP.Failed_AVP> errors = listCreate(Base.AVP.Failed_AVP);

    // Get MSISDN and IMSI
    if (in.Subscription_Id != null
    && listSize(in.Subscription_Id) > 0) {
        int i = 0;
        while (i < listSize(in.Subscription_Id)) {
            AVP.Subscription_Id item = listGet(in.Subscription_Id, i);
            if (item.Subscription_Id_Type == END_USER_E164) {
                rc.ccr.msisdn = item.Subscription_Id_Data;
            } else if (item.Subscription_Id_Type == END_USER_IMSI) {
                rc.ccr.imsi = item.Subscription_Id_Data;
            }
            i = i + 1;
        }
    }

    // Missing IMSI
    if (rc.ccr.imsi == null) {
        AVP.Subscription_Id error = udrCreate(AVP.Subscription_Id);
        error.Subscription_Id_Type = END_USER_IMSI;
        error.Subscription_Id_Data = "Missing IMSI";
        Base.AVP.Failed_AVP failed = udrCreate(Base.AVP.Failed_AVP);
        failed.Additional_AVPs = listCreate(any, error);
        listAdd(errors, failed);
        debug("extractCCR() ERROR: missing IMSI");
        listAdd(rc.errorCodes, ERR_LOG_MISSING_IMSI);
    }

    // Missing MSISDN, only if this is used as subscriber key
    if (rc.ccr.msisdn == null && SUBSCRIBER_KEY == END_USER_E164) {
        AVP.Subscription_Id error = udrCreate(AVP.Subscription_Id);
        error.Subscription_Id_Type = END_USER_E164;
        error.Subscription_Id_Data = "Missing MSISDN";
        Base.AVP.Failed_AVP failed = udrCreate(Base.AVP.Failed_AVP);
        failed.Additional_AVPs = listCreate(any, error);
        listAdd(errors, failed);
        debug("extractCCR() ERROR: missing MSISDN");
        listAdd(rc.errorCodes, ERR_LOG_MISSING_MSISDN);
    }

    // Set subscriber key
    // This is configuable using configuration parameters
    if (SUBSCRIBER_KEY == END_USER_E164) {
        rc.subscriberKey = rc.ccr.msisdn;
    } else {
        rc.subscriberKey = rc.ccr.imsi;
    }

    // Bearer-Identifier
    if (udrIsPresent(in.Bearer_Identifier)) {
        rc.ccr.Bearer_Identifier = in.Bearer_Identifier;
    }

    // 3GPP-User-Location-Info
    if (udrIsPresent(in.3GPP_User_Location_Info)) {
        rc.ccr.TGPP_User_Location_Info = baToHexString(in.3GPP_User_Location_Info);
    }

    // User-Equipment-Info
    if (udrIsPresent(in.User_Equipment_Info)) {
        rc.ccr.User_Equipment_Info =
            (string)in.User_Equipment_Info.User_Equipment_Info_Type
            + DELIMITER
            + baToHexString(in.User_Equipment_Info.User_Equipment_Info_Value);
    }

    // 3GPP-SGSN-MCC-MNC
    if (udrIsPresent(in.3GPP_SGSN_MCC_MNC)) {
        rc.ccr.TGPP_SGSN_MCC_MNC = in.3GPP_SGSN_MCC_MNC;
    }

    // RAT-Type
    if (udrIsPresent(in.RAT_Type)) {
        rc.ccr.RAT_Type = in.RAT_Type;
    }

    // Create internal session destination/origin
    rc.Destination = in.Origin_Host
        + DELIMITER + in.Origin_Realm;

    // Usage-Monitoring-Information
    if (udrIsPresent(in.Usage_Monitoring_Information)
    && in.Usage_Monitoring_Information != null
    && listSize(in.Usage_Monitoring_Information) > 0) {
        rc.ccr.umi = listCreate(umi);
        int i = 0;
        while (i < listSize(in.Usage_Monitoring_Information)) {
            AVP.Usage_Monitoring_Information item = listGet(in.Usage_Monitoring_Information, i);
            // Monitoring-Key and reported usage must be present
            if (item.Monitoring_Key != null
            && udrIsPresent(item.Used_Service_Unit)
            && item.Used_Service_Unit != null
            && listSize(item.Used_Service_Unit) > 0) {

                // Internal Usage-Monitoring-Information item
                umi umi = udrCreate(umi);
                listAdd(rc.ccr.umi, umi);

                // Monitoring-Key, convert to string from bytearray
                umi.monitoringKey = baToStr(item.Monitoring_Key);

                // Count USU
                int j = 0;
                while (j < listSize(item.Used_Service_Unit)) {
                    AVP.Used_Service_Unit usu = listGet(item.Used_Service_Unit, j);
                    if (udrIsPresent(usu.CC_Input_Octets)) {
                        umi.input = umi.input + usu.CC_Input_Octets;
                    }
                    if (udrIsPresent(usu.CC_Output_Octets)) {
                        umi.output = umi.output + usu.CC_Output_Octets;
                    }
                    if (udrIsPresent(usu.CC_Total_Octets)) {
                        umi.total = umi.total + usu.CC_Total_Octets;
                    }
                    j = j + 1;
                }

                // Sum CC-Input-Octets and CC-Output-Octets, only if CC-Total-Octets missing from network
                if (SUM_OCTETS && umi.total == 0) {
                    umi.total = umi.input + umi.output;
                }
            }
            i = i + 1;
        }
    }

    // Validation failed
    if (listSize(errors) > 0) {
        rc.cca.Failed_AVP = errors;
        rc.cca.Result_Code = DIAMETER_MISSING_AVP;
        debug("extractCCR() validation failed with errors = " + errors);
        return false;
    }

    // CCR extracted without errors
    debug("extractCCR() CCR " + rc.ccr);
    return true;
}


/*
 * Purpose:  Create CCA according to network diameter specification from internal CCA
 *          
 * Assumes:  Nothing
 *
 * Effects:  Nothing
 *
 * Comments: 
 *
 */
CC_Answer createCCA(rc rc) {
    // Missing input
    if (rc == null || rc.cca == null) {
        debug("createCCA() Invalid input: [" + rc + "]");
        return null;
    }

    // CCA for network
    CC_Answer cca = udrCreate(CC_Answer);
    cca.Session_Id = rc.cca.Session_Id;
    cca.CC_Request_Type = rc.cca.CC_Request_Type;
    cca.CC_Request_Number = rc.cca.CC_Request_Number;
    cca.Auth_Application_Id = rc.cca.Auth_Application_Id;
    cca.Result_Code = rc.cca.Result_Code;

    // Event-Trigger
    if (rc.cca.Event_Trigger != null && listSize(rc.cca.Event_Trigger) > 0) {
        cca.Event_Trigger = rc.cca.Event_Trigger;
    }

    // Usage-Monitoring-Information
    if (rc.cca.umi != null && listSize(rc.cca.umi) > 0) {
        cca.Usage_Monitoring_Information = createUsageMonitoringInfo(rc.cca.umi);
    }

    // Charging-Rule-Install
    if (rc.cca.rulesInstall != null && listSize(rc.cca.rulesInstall) > 0) {
        cca.Charging_Rule_Install = createChargingRuleInstall(rc.cca.rulesInstall, rc.Bearer_Identifier, rc.cca.ruleDeactTimeMap);
    }

    // Charging-Rule-Remove
    if (rc.cca.rulesRemove != null && listSize(rc.cca.rulesRemove) > 0) {
        cca.Charging_Rule_Remove = createChargingRuleRemove(rc.cca.rulesRemove);
    }

    // QoS-Information
    if (rc.cca.qos != null) {
        cca.QoS_Information = createQoSInformation(rc.cca.qos, rc.Bearer_Identifier);
    }

    // Failed-AVP
    if (rc.cca.Failed_AVP != null && listSize(rc.cca.Failed_AVP) > 0) {
        cca.Failed_AVP = rc.cca.Failed_AVP;
    }

    debug("createCCA() CCA created");
    return cca;
}


/*
 * Purpose:  Create network RAR from internal RAR
 *          
 * Assumes:  Nothing
 *
 * Effects:  Nothing
 *
 * Comments: 
 *
 */
RA_Request createRAR(rar in) {
    // Missing input
    if (in == null) {
        debug("createRAR() Missing input internal RAR");
        return null;
    }

    // Create network RAR
    RA_Request rar = udrCreate(RA_Request);
    rar.Session_Id = in.Session_Id;
    rar.Destination_Host = in.Destination_Host;
    rar.Destination_Realm = in.Destination_Realm;

    // Charging-Rule-Install
    if (in.rulesInstall != null && listSize(in.rulesInstall) > 0) {
        rar.Charging_Rule_Install = createChargingRuleInstall(in.rulesInstall, in.Bearer_Identifier, in.ruleDeactTimeMap);
    }

    // Charging-Rule-Remove
    if (in.rulesRemove != null && listSize(in.rulesRemove) > 0) {
        rar.Charging_Rule_Remove = createChargingRuleRemove(in.rulesRemove);
    }

    // QoS-Information
    if (in.qos != null) {
        rar.QoS_Information = createQoSInformation(in.qos, in.Bearer_Identifier);
    }

    // Usage-Monitoring-Report
    AVP.Usage_Monitoring_Information umi = udrCreate(AVP.Usage_Monitoring_Information);
    umi.Usage_Monitoring_Report = USAGE_MONITORING_REPORT_REQUIRED;
    rar.Usage_Monitoring_Information = listCreate(AVP.Usage_Monitoring_Information, umi);
   
    return rar;
}


/*
 * Purpose:  Create Charging-Rule-Install AVP from PCRF rules list
 *          
 * Assumes:  Nothing
 *
 * Effects:  Nothing
 *
 * Comments: 
 *
 */
list<AVP.Charging_Rule_Install> createChargingRuleInstall(list<Static_Rule> rules, bytearray bearer, map<int, date> ruleDeactTimeMap) {
    if (rules == null || listSize(rules) < 1) {
        return null;
    }
    list<AVP.Charging_Rule_Install> out = listCreate(AVP.Charging_Rule_Install);
    int i = 0;
    while (i < listSize(rules)) {
        Static_Rule rule = listGet(rules, i);
        AVP.Charging_Rule_Install cri = udrCreate(AVP.Charging_Rule_Install);
        if (bearer != null) {
            cri.Bearer_Identifier = bearer;
        }
        if (rule.Rule_Base_Name != null && strLength(rule.Rule_Base_Name) > 0) {
            if (cri.Charging_Rule_Base_Name == null) {
                cri.Charging_Rule_Base_Name = listCreate(string);
            }
            listAdd(cri.Charging_Rule_Base_Name, rule.Rule_Base_Name);
            listAdd(out, cri);
        } else if (rule.Rule_Name != null && strLength(rule.Rule_Name) > 0) {
            if (cri.Charging_Rule_Name == null) {
                cri.Charging_Rule_Name = listCreate(bytearray);
            }
            bytearray rulename = baCreate(0);
            strToBA(rulename, rule.Rule_Name);
            listAdd(cri.Charging_Rule_Name, rulename);
            listAdd(out, cri);
        }
        if(ruleDeactTimeMap != null && mapGet(ruleDeactTimeMap, rule.ID) != null) {
            debug("createChargingRuleInstall() Deactivation time found for static rule : " + mapGet(ruleDeactTimeMap, rule.ID));
            cri.Rule_Deactivation_Time = mapGet(ruleDeactTimeMap, rule.ID);
        }

        i = i + 1;
    }
    return out;
}


/*
 * Purpose:  Create Charging-Rule-Remove AVP from PCRF rules list
 *          
 * Assumes:  Nothing
 *
 * Effects:  Nothing
 *
 * Comments: 
 *
 */
list<AVP.Charging_Rule_Remove> createChargingRuleRemove(list<Static_Rule> rules) {
    if (rules == null || listSize(rules) < 1) {
        return null;
    }
    list<AVP.Charging_Rule_Remove> out = listCreate(AVP.Charging_Rule_Remove);
    AVP.Charging_Rule_Remove crr = udrCreate(AVP.Charging_Rule_Remove);
    crr.Charging_Rule_Name = listCreate(bytearray);
    int i = 0;
    while (i < listSize(rules)) {
        Static_Rule rule = listGet(rules, i);
        if (rule.Rule_Base_Name != null && strLength(rule.Rule_Base_Name) > 0) {
            if (crr.Charging_Rule_Base_Name == null) {
                crr.Charging_Rule_Base_Name = listCreate(string);
            }
            listAdd(crr.Charging_Rule_Base_Name, rule.Rule_Base_Name);
        } else if (rule.Rule_Name != null && strLength(rule.Rule_Name) > 0) {
            if (crr.Charging_Rule_Name == null) {
                crr.Charging_Rule_Name = listCreate(bytearray);
            }
            bytearray rulename;
            strToBA(rulename, rule.Rule_Name);
            listAdd(crr.Charging_Rule_Name, rulename);
        }
        i = i + 1;
    }
    listAdd(out, crr);
    return out;
}


/*
 * Purpose:  Create QoS-Information AVP from PCRF QoS
 *          
 * Assumes:  Nothing
 *
 * Effects:  Nothing
 *
 * Comments: 
 *
 */
list<AVP.QoS_Information> createQoSInformation(QoS_Information in, bytearray bearer) {
    if (in == null) {
        return null;
    }
    AVP.QoS_Information qos = udrCreate(AVP.QoS_Information);
    qos.QoS_Class_Identifier = in.QCI;
    if (bearer != null) {
        qos.Bearer_Identifier = bearer;
    }
    qos.Max_Requested_Bandwidth_DL = (int)in.MBR_DL;
    qos.Max_Requested_Bandwidth_UL = (int)in.MBR_UL;
    qos.Guaranteed_Bitrate_DL = (int)in.GBR_DL;
    qos.Guaranteed_Bitrate_UL = (int)in.GBR_UL;
    qos.APN_Aggregate_Max_Bitrate_DL = (int)in.APN_Agg_MBR_DL;
    qos.APN_Aggregate_Max_Bitrate_UL = (int)in.APN_Agg_MBR_UL;
    return listCreate(AVP.QoS_Information, qos);
}


/*
 * Purpose:  Create Usage-Monitoring-Information AVP from internal UDR
 *          
 * Assumes:  Nothing
 *
 * Effects:  Nothing
 *
 * Comments: 
 *
 */
list<AVP.Usage_Monitoring_Information> createUsageMonitoringInfo(list<umi> in) {
    if (in == null || listSize(in) < 1) {
        return null;
    }
    list<AVP.Usage_Monitoring_Information> out = listCreate(AVP.Usage_Monitoring_Information);
    int i = 0;
    while (i < listSize(in)) {
        umi item = listGet(in, i);
        AVP.Usage_Monitoring_Information umi = udrCreate(AVP.Usage_Monitoring_Information);
        listAdd(out, umi);

        // Monitoring-Key
        strToBA(umi.Monitoring_Key, item.monitoringKey);

        // Usage-Monitoring-Level
        if (udrIsPresent(item.Usage_Monitoring_Level)) {
            umi.Usage_Monitoring_Level = item.Usage_Monitoring_Level;
        }

        // Usage-Monitoring-Report
        if (udrIsPresent(item.Usage_Monitoring_Report)) {
            umi.Usage_Monitoring_Report = item.Usage_Monitoring_Report;
        }

        // Usage-Monitoring-Support
        if (udrIsPresent(item.Usage_Monitoring_Support)) {
            umi.Usage_Monitoring_Support = item.Usage_Monitoring_Support;
        }

        // Granted-Service-Unit
        AVP.Granted_Service_Unit gsu = udrCreate(AVP.Granted_Service_Unit);
        boolean gsuPresent = false;
        if (udrIsPresent(item.Monitoring_Time)) {
            gsu.Monitoring_Time = item.Monitoring_Time;
        }
        if (item.input > 0) {
            gsu.CC_Input_Octets = item.input;
            gsuPresent = true;
        }
        if (item.output > 0) {
            gsu.CC_Output_Octets = item.output;
            gsuPresent = true;
        }
        if (item.total > 0) {
            gsu.CC_Total_Octets = item.total;
            gsuPresent = true;
        }
        if (gsuPresent) {
            umi.Granted_Service_Unit = listCreate(AVP.Granted_Service_Unit, gsu);
        }

        i = i + 1;
    }
    return out;
}


