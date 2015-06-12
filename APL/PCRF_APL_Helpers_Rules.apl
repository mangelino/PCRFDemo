/*
 * Module:                 PCRF_APL_Helpers_Rules
 *
 * Date Created:           2012
 *
 * Author:                 DigitalRoute
 *
 * Purpose:                Functions for rules handling
 *
 * Dependencies:           None
 *
 * Issues:                 None                             
 *
 * Comments:               Gx diameter functionality is based on 3GPP TS 29.212 V11.6.0 (2012-09), Release 11
 */


import ultra.PCC.Buckets;
import ultra.PCC.Products;
import ultra.PCC.Periods;
import ultra.PCRF.Rules;
import ultra.Policy_Templates.PCRF_UFL_Internal;

import apl.Policy_Templates.PCRF_APL_Configuration;
import apl.Policy_Templates.PCRF_APL_Constants;
import apl.Policy_Templates.PCRF_APL_Functions;
import apl.Policy_Templates.PCRF_APL_Helpers;
import apl.Policy_Templates.PCRF_APL_User_Functions;


/*
 * Purpose:  Gx rules processing - retrieve all current rules and compare to installed rules
 *          
 * Assumes:  Nothing
 *
 * Effects:  Nothing
 *
 * Comments: 
 *
 */
void processRules(rc rc) {
    debug("processRules() START");

    // Invalid input
    if (rc == null) {
        debug("processRules() ERROR invalid input");
        return;
    }

    // Get subscriber BDH
    BucketDataHolder bdh = mapGet(rc.bdh, rc.subscriberKey);
    if (bdh == null) {
        debug("processRules() ERROR subscriber BDH is missing");
        return;
    }

    // Get session
    Session session = getSession(bdh, rc.ccr.Session_Id);
    if (session == null) {
        debug("processRules() ERROR subscriber session is missing");
        return;
    }

    map<int, date> pccRuleDeactMap = mapCreate(int, date);
    // Get rules
    list<PCC_Rule> rules = getRules(rc.bdh, rc.timestamp, pccRuleDeactMap, rc.ccr.Home_Location_Flag); // USE CASE 5

    // Check rules for curent session
    updateRules out = checkRules(session, rules, pccRuleDeactMap);

    // No changes in rules
    if (out == null) {
        debug("processRules() END no changes in rules");
        return;
    }

    rc.cca.rulesInstall = out.rulesInstall;
    rc.cca.rulesRemove = out.rulesRemove;
    rc.cca.qos = out.qos;
    rc.cca.qos_old = out.qos_old;
    rc.cca.ruleDeactTimeMap = out.statRuleDeactMap;

    debug("processRules() END");
}


/*
 * Purpose:  Create list of internal RAR for subscriber key, only rules are preent in RAR
 *          
 * Assumes:  Nothing
 *
 * Effects:  Nothing
 *
 * Comments: 
 *
 */
list<rar> processRar(internalRAR intRar, list<int> errorCodes) {
    debug("processRar() START");
    string subscriberKey = intRar.subscriberKey;
    string actionType = intRar.actionType;

    // Subscriber key is missing
    if (subscriberKey == null) {
        debug("processRar() ERROR Subscriber Key is missing");
        return null;
    }

    // Get BDH - read-only access
    BucketDataHolder subscriberBdh = pccBucketDataLookup(subscriberKey, null);
    if (subscriberBdh == null || subscriberBdh.Subscriber == null) {
        debug("processRar() ERROR subscriber does not exist or invalid = " + subscriberKey);
        return null;
    }

    // Subscribers list
    list<string> subscribers = listCreate(string);

    // Extract members if group BDH
    if (subscriberBdh.Subscriber.Misc != null
    && mapGet(subscriberBdh.Subscriber.Misc, MISC_MEMBERS) != null) {
        list<string> parts = strSplit((string)mapGet(subscriberBdh.Subscriber.Misc, MISC_MEMBERS), DELIMITER);
        int j = 0;
        while (j < listSize(parts)) {
            string member = listGet(parts, j);
            if (member != null && strLength(member) > 0) {
                listAddNoDup(subscribers, member);
            }
            j = j + 1;
        }

    // Add single list item if subscriber
    } else {
        listAdd(subscribers, subscriberKey);
    }
    debug("processRar() subscribers to check = " + subscribers);

    // Members not found
    if (listSize(subscribers) < 1) {
        debug("processRar() ERROR missing members for = " + subscriberKey);
        if(errorCodes != null) {
            listAdd(errorCodes, ERR_LOG_MISSING_MEMBERS);
        }
        return null;
    }

    // Start transaction
    any txn = pccBeginBucketDataTransaction();
    if (txn == null) {
        debug("processRar() ERROR failed to create transaction");
        return null;
    }

    // RAR list
    list<rar> out = listCreate(rar);

    // Loop thru subscribers list and create RARs for active sessions
    int i = 0;
    while (i < listSize(subscribers)) {
        string subscriber = listGet(subscribers, i);

        // Subscriber BDH
        BucketDataHolder bdh = pccBucketDataLookup(subscriber, txn);

        // BDH map
        map<string, BucketDataHolder> bdhMap = mapCreate(string, BucketDataHolder);

        // Add subscriber UDR to BDH map
        mapSet(bdhMap, subscriber, bdh);

        // Valid BDH with sessions and subscriber UDR
        if (bdh != null && bdh.Sessions != null && listSize(bdh.Sessions) > 0
        && bdh.Subscriber != null) {

            // Check validity and reset times for buckets
            processBucketsReset(bdh, true, dateCreateNow(), null);

            // Remove old sessions
            removeOldSessions(bdh, PROTOCOL_GX, TIMEOUT_SESSION_GX);

            // Add subscriber groups to BDH map if present
            if (bdh.Subscriber.Groups != null) {
                int j = 0;
                while (j < listSize(subscriberBdh.Subscriber.Groups)) {
                    // Get group BDH
                    string groupId = listGet(subscriberBdh.Subscriber.Groups, j);
                    BucketDataHolder groupBdh = pccBucketDataLookup(groupId, txn);

                    // Group BDH is present with buckets
                    if (groupBdh != null && groupBdh.Buckets != null) {
                        mapSet(bdhMap, groupId, groupBdh);
                        debug("processRar() Group BDH added = " + groupId);

                    // Unlock empty group BDH
                    } else {
                        pccBucketDataStore(groupId, groupBdh, txn);
                    }
                    j = j + 1;
                }
            }

            // Loop thru subscriber sessions
            int k = 0;
            while (k < listSize(bdh.Sessions)) {
                Session session = listGet(bdh.Sessions, k);

                // Get session Bearer-Identifier
                bytearray bearer;
                if (session.Misc != null && mapContains(session.Misc, MISC_BEARER_ID)) {
                    bearer = hexStringToBA((string)mapGet(session.Misc, MISC_BEARER_ID));
                }

                // Split destination into host and realm
                list<string> parts = strSplit(session.Destination, DELIMITER);
                if (listSize(parts) == 2) {
                    map<int, date> pccRuleDeactTimeMap = mapCreate(int, date);
                    // Get rules
                    list<PCC_Rule> rules = getRules(bdhMap, dateCreateNow(), pccRuleDeactTimeMap, 0); //USE CASE 5 - hardcoded 0 value

                    // Check rules for curent session
                    updateRules update = checkRules(session, rules, pccRuleDeactTimeMap);

                    // If rules changed create internal RAR
                    if ((update != null && update.changed) || 
                            actionType == RAR_TYPE_REMOVE_GROUP || 
                            actionType == RAR_TYPE_ADD_GROUP) {
                        rar rar = udrCreate(rar);
                        rar.Session_Id = session.ID;
                        rar.Destination_Host = listGet(parts, 0);
                        rar.Destination_Realm = listGet(parts, 1);
                        rar.Bearer_Identifier = bearer;
                        if(update != null && update.changed) {
                            rar.rulesInstall = update.rulesInstall;
                            rar.rulesRemove = update.rulesRemove;
                            rar.qos_old = update.qos_old;
                            rar.qos = update.qos;
                            rar.ruleDeactTimeMap = update.statRuleDeactMap;
                        }
                        listAdd(out, rar);
                    }
                }
                k = k + 1;
            }
        }

        // Close all BDH
        if (bdh != null) {
            int j = 0;
            list<string> keys = mapKeys(bdhMap);
            while (j < listSize(keys)) {
                string key = listGet(keys, j);
                BucketDataHolder b = mapGet(bdhMap, key);
                pccBucketDataStore(key, b, txn);
                j = j + 1;
            }
        }

        i = i + 1;
    }

    // Commit transaction
    pccCommitBucketDataTransaction(txn);
    debug("processRar() Transaction commited");

    debug("processRar() END rars = " + listSize(out));
    return out;
}


/* 
 * Purpose:  Compare current rules with installed rules, if differences
 *           found then return rules and QoS AVPs for CCA
 *           
 * Assumes:  Nothing 
 * 
 * Effects:  Nothing 
 * 
 * Comments: 
 * 
 */ 
updateRules checkRules(Session session, list <PCC_Rule> rules, map<int, date> pccRuleDeactTimeMap) {
    debug("checkRules() START");

    // Missing input
    if (session == null) {
        debug("checkRules() ERROR missing input");
        return null;
    }

    // Get Bearer_Identifier from session
    bytearray Bearer_Identifier;
    if (session.Misc != null && mapContains(session.Misc, MISC_BEARER_ID)) {
        Bearer_Identifier = hexStringToBA((string)mapGet(session.Misc, MISC_BEARER_ID));
    }

    // In case there are no current rules, then necessary to
    // check if some rules shall not be removed 
    if (rules == null) {
        rules = listCreate(PCC_Rule);
    }

    //sattic rule daectivation time map
    map<int, date> statRuleDeactMap = mapCreate(int, date);

    // Find installed Rule from session matching bearer
    // This object is referene to subscriber session
    InstalledRule installedRule = getInstalledRule(session, Bearer_Identifier);
    if (installedRule == null) {
        debug("checkRules() installed rule is NULL");
        return null;
    }
    debug("checkRules() Installed rule in session (PCC Rules & QoS): " + installedRule);

    // Get all installed static rules from session
    map<int, Static_Rule> installedStatic = mapCreate(int, Static_Rule);
    int i = 0;
    while (i < listSize(installedRule.Rules)) {
        int ruleId = listGet(installedRule.Rules, i);
        PCC_Rule pccRule = (PCC_Rule)pccGetUdr("PCRF.Rules.PCC_Rule", ruleId);
        if (pccRule != null && pccRule.Charging_Rules != null) {
            int j = 0;
            while (j < listSize(pccRule.Charging_Rules)) {
                Charging_Rule chargingRule = listGet(pccRule.Charging_Rules, j);
                if (chargingRule.Static_Rule != null) {
                    mapSet(installedStatic, chargingRule.Static_Rule.ID, chargingRule.Static_Rule);
                }
                j = j + 1;
            }
            // TODO shall we check installed QoS
        }
        i = i + 1;
    }

    // Get list of new static rules and QoS (from rules mapping and enforcements)
    map<int, Static_Rule> newStatic = mapCreate(int, Static_Rule);
    QoS_Information qos;
    list<int> newPccRule = listCreate(int);
    i = 0;
    while (i < listSize(rules)) {
        PCC_Rule pccRule = listGet(rules, i);

        // Charging rules are present
        if (pccRule.Charging_Rules != null) {
            boolean found = false;
            int j = 0;
            while (j < listSize(pccRule.Charging_Rules)) {
                Charging_Rule chargingRule = listGet(pccRule.Charging_Rules, j);

                // Find static rule
                if (chargingRule.Static_Rule != null) {
                    mapSet(newStatic, chargingRule.Static_Rule.ID, chargingRule.Static_Rule);
                    found = true;
                }
                // add deactivation date of static rule
                if(pccRuleDeactTimeMap != null && statRuleDeactMap != null && mapGet(pccRuleDeactTimeMap, pccRule.ID) != null) {
                    debug("CheckRules() Satic_Rule ID = " + chargingRule.Static_Rule.ID + " set deactivation time to: " + mapGet(pccRuleDeactTimeMap, pccRule.ID));
                    mapSet(statRuleDeactMap, chargingRule.Static_Rule.ID, mapGet(pccRuleDeactTimeMap, pccRule.ID));
                }
                // TODO in future here can be added check for dynamic rules
                j = j + 1;
            }

            // Current PCC Rule holds static rule
            // TODO do we need to set PCC Rule ID in installedRules for QoS or only Static Rules?
            if (found) {
                listAdd(newPccRule, pccRule.ID);
            }
        }

        // Take first QoS in case multiple available
        if (qos == null && pccRule.QoS != null) {
            qos = pccRule.QoS;
        }
        i = i + 1;
    }

    // Get list of static rules to remove, rules present in install list but missing in new rules list
    list<Static_Rule> removeStatic = listCreate(Static_Rule);
    i = 0;
    list<int> keys = mapKeys(installedStatic);
    while (i < listSize(keys)) {
        int ruleId = listGet(keys, i);
        if (!mapContains(newStatic, ruleId)) {
            listAddNoDup(removeStatic, mapGet(installedStatic, ruleId));
        }
        i = i + 1;
    }

    // Create list of Static rules to install -  present in newStatic list but missing in installedStatic list
    list<Static_Rule> installStatic = listCreate(Static_Rule);
    i = 0;
    keys = mapKeys(newStatic);
    while (i < listSize(keys)) {
        int ruleId = listGet(keys, i);
        if (!mapContains(installedStatic, ruleId)) {
            listAddNoDup(installStatic, mapGet(newStatic, ruleId));
        }
        i = i + 1;
    }

    debug("checkRules() New PCC Rules to install into session = " + newPccRule);
    debug("checkRules() Already installed Static Rules = " + mapKeys(installedStatic));
    debug("checkRules() New Static Rules = " + mapKeys(newStatic));
    debug("checkRules() New Static Rules to install = " + installStatic);
    debug("checkRules() Static Rules to remove = " + removeStatic);
    debug("checkRules() QoS_Information: " + qos);
    debug("checkRules() Static Rules Deactivation Time: " + statRuleDeactMap);

    // Set new installed rules into session
    // This object is referene to subscriber session
    installedRule.Rules = newPccRule;

    // Output UDR
    updateRules out = udrCreate(updateRules);
    out.changed = false;

    // Charging-Rules-Install AVP
    if (listSize(installStatic) > 0) {
        out.rulesInstall = installStatic;
        out.changed = true;
    }

    // Charging-Rules-Remove AVP
    if (listSize(removeStatic) > 0) {
        out.rulesRemove = removeStatic;
        out.changed = true;
    }

    // QoS-Information
    // Only in case new QoS exists and is different from installed one
    // However there is no way to uninstall QoS, we can only change it once installed
    if ((qos != null && qos.ID != installedRule.QoS)) {
//    || (qos == null && installedRule.QoS != 0)) {
        out.changed = true;
        QoS_Information qosInstalled = (QoS_Information)pccGetUdr("PCRF.Rules.QoS_Information", installedRule.QoS);
        out.qos_old = qosInstalled;
        installedRule.QoS = qos.ID;
        out.qos = qos;
        debug("checkRules() QoS changed = TRUE");
    }
//    if (qos != null) {
//        installedRule.QoS = qos.ID;
//        out.qos = qos;
//    }
    if(statRuleDeactMap != null) {
        out.statRuleDeactMap = statRuleDeactMap;
    }

    debug("checkRules() END = " + out.changed);
    return out;
}


/* 
 * Purpose:  This is the main enforcement calculation function. It will take the 
 *           rulesmapping and the current buckets to calculate the current rules
 *           that should be active.
 *           
 * Assumes:  Nothing 
 * 
 * Effects:  Nothing 
 * 
 * Comments: 
 * 
 */
list<PCC_Rule> getRules(map<string, BucketDataHolder> bdhMap, date timestamp, map<int, date> ruleDeactTimeMap, int isAtHome) {

    // to set be set, if rule belongs to add-on product
    map<int, date> bckProdEndTimeMap = mapCreate(int, date);

    debug("getRules() START");

    // Missing input
    if (bdhMap == null || mapSize(bdhMap) < 1) {
        debug("getRules() ERROR missing input");
        return null;
    }

    // Step 1:
    // Calculate enforcements from buckets, and build a product list
    // For each valid bucket get 1 enforcement, if no enforcements match then use default enforcement
    map<int, string> enfProd = mapCreate(int, string);
    int i = 0;
    list<string> keys = mapKeys(bdhMap);
    while (i < listSize(keys)) {
        string subscriberKey = listGet(keys, i);
        BucketDataHolder bdh = mapGet(bdhMap, subscriberKey);
        debug("getRules() START BDH = " + subscriberKey);
        int j = 0;
        while(j < listSize(bdh.Buckets)) {
            Bucket b = listGet(bdh.Buckets, j);
            Product p = (Product)pccGetUdr("PCC.Products.Product", b.Product);
            debug("getRules() bucket=" + b.ID + ", product=" + b.Product);

            if (p != null && isProductActive(p.Periods, timestamp) && isValidBucket(b, p, timestamp)) {

                // Adding default enforcement to all the products before checking which enforcement has been triggered
                // TODO do we need this? maybe it shall be configured as *;*;* in rules mapping
                mapSet(enfProd, p.ID, ENF_DEFAULT);

                // Get bucket counter
                Counter c = getBucketCounter(b);

                // Loop thru all counter types and find matching enforcments
                if (c != null && p.Enforcements != null && listSize(p.Enforcements) != 0) {
                    int k = 0;
                    list<byte> usageKeys = mapKeys(c.Usage);
                    while (k < listSize(usageKeys)) {
                        byte counterType = listGet(usageKeys, k);
                        long enfLevel = -1;
                        int l = 0;
                        while (l < listSize(p.Enforcements)) {
                            Enforcement e = listGet(p.Enforcements, l);
                            // Enforcement is for current counterType
                            if (e.CounterType == counterType) {

                                // Get capacity for product
                                Capacity cap = getCapacityByType(p.Capacities, counterType);
                                long capacity = 0;
                                if (cap != null) {
                                    capacity = convertToBytes(cap.Capacity, cap.CapacityUnit);
                                }

                                // Enforcement level in bytes
                                // If enforcement Level > 1 then its absolute value
                                // If enforcement Level <= 1 then its relative value (percentage)
                                long levelVal;
                                if (e.Level <= 1) {
                                    levelVal = (long)(capacity * e.Level);
                                } else {
                                    levelVal = (long)e.Level;
                                }

                                // Bucket counter value
                                long counterVal = mapGet(c.Usage, counterType);
                                debug("getRules() Enforcement = " + e.Name + ", capacity = " + capacity + ", level = " + levelVal + ", counter = " + counterVal);

                                // Threshold reached
                                // And this is the highest enforcement we have sofar, for this countertype
                                if (counterVal >= levelVal && levelVal > enfLevel) {
                                    debug("getRules() add enforcement [" + e.Name + "] with level [" + e.Level + "] for product [" + p.Name + "][" + p.ID + "]");
                                    // Store the enforcements. No need for duplicate check since
                                    // any higher enforcement will overwrite the old one for that product.
                                    mapSet(enfProd, p.ID, e.Name);
                                    enfLevel = levelVal;
                                    // if product type is Add-on, then store bucket end time for rule deactivation
                                    if(p.ResetInterval <= 0) {
                                        date deactTime = mapGet(bckProdEndTimeMap, p.ID);
                                        if(deactTime == null) {
                                            debug("getRules() First enforcement for add-on product found, set stop time to " + b.StopTime);
                                            mapSet(bckProdEndTimeMap, p.ID, b.StopTime);
                                        } else {
                                            //for each product, store only stopTime to be the closest one
                                            if(dateDiff(deactTime, b.StopTime) > 0) {
                                                debug("getRules() New stopTime for add-on product enforcement found, set stop time to " + b.StopTime + " from " + deactTime);
                                                mapSet(bckProdEndTimeMap, p.ID, b.StopTime);
                                            }
                                        }
                                    }
                                }
                            }
                            l = l + 1;
                        }
                        k = k + 1;
                    }
                }
            }
            j = j + 1;
        }
        debug("getRules() END BDH = " + subscriberKey);
        i = i + 1;
    }
    debug("getRules() enfProd: " + enfProd);
    debug("getRules() rule Deactivation Time Map: " + ruleDeactTimeMap);

    if (mapSize(enfProd) < 1) {
        debug("getRules() END no proucts and enforcements");
        return null;
    }

    // Step 2:
    // We now have a product list with enforcements
    // For each rules mapping row find relevant products/enforcements
    // Rule mapping is sorted by priorities
    // There are 2 arguments in rules mapping, those can be wildcard(*):
    //  - productID
    //  - enforcement
    // TODO this shall be configurable per customer, because arguments can be different for each customer, like RAT-Type, MCC/MNC

    // Get product mapping
    list<drudr> mapping = pccGetUdrList("PCRF.Rules.RulesMapping");

    // Sort mapping by priority
    listSort(mapping, Priority, ascending, RulesMapping);

    // For each rules mapping find matching product/enforcement
    // If matching rules found and StopFallthrough flag fo rules mapping row
    // is set then do not add more rules to output
    boolean stopFallthrough = false;
    list<PCC_Rule> rules = listCreate(PCC_Rule);
    i = 0;
    while (i < listSize(mapping) && !stopFallthrough) {
        RulesMapping rm = (RulesMapping)listGet(mapping, i);
        debug("getRules() Rules maping row with priority = " + rm.Priority);

        // Now check all products/enforcements if match current rules mapping arguments
        int j = 0;
        list<int> items = mapKeys(enfProd);
        while (j < listSize(items)) {
            int product = listGet(items, j);
            string enforcement = mapGet(enfProd, product);

            // Create enforcement arguments
            // TODO probably for each customer we can create different list - listCreate(string, (string)product, enforcement, rc.ratType, rc.mccMnc);
            list<string> arguments = listCreate(string, (string)product, enforcement, (string)isAtHome); //USE CASE 5
            debug("getRules() arguments = " + arguments);

            // Check if arguments match
            if (rm.Targets != null && matchArguments(rm.Arguments, arguments)) {
                int k = 0;
                while (k < listSize(rm.Targets)) {
                    PCC_Rule rule = listGet(rm.Targets, k);

                    // Only rules with active periods are selected
                    if (isActivePeriod(rule.Period, timestamp)) {
                        listAddNoDup(rules, rule);
                        debug("getRules() Add rule = " + rule.Rule_Name + ", enforcement = "
                            + enforcement + ", product = " + product);

                        //set rule deactivation time if it belongs to add-on product stored in 1st step
                        if(ruleDeactTimeMap != null && bckProdEndTimeMap != null &&  mapGet(bckProdEndTimeMap, product) != null) {
                            debug("getRules() Rule for Add-on bucket found, set end time to " + mapGet(bckProdEndTimeMap, product));
                            mapSet(ruleDeactTimeMap, rule.ID, mapGet(bckProdEndTimeMap, product));
                        }

                        // If StopFallthrough flag is set then no more rules
                        if (rm.StopFallthrough) {
                            stopFallthrough = rm.StopFallthrough;
                            debug("getRules() stopFallthrough = TRUE");
                        }
                    }
                    k = k + 1;
                }
            }
            j = j + 1;
        }
        i = i + 1;
    }
    debug("getRules() number of PCC Rules found = " + listSize(rules));
    debug("getRules() PCC Rules = " + rules);

    // Rules found
    if (listSize(rules) > 0) {
        debug("getRules() END Rules found");
        return rules;
    }

    // Rules not found
    debug("getRules() END Rules NOT found");
    return null;
}


/*
 * Purpose:  Retrieve InstalledRule for bearer from session, if missing create new
 *          
 * Assumes:  Nothing
 *
 * Effects:  Nothing
 *
 * Comments: Returns reference to session InstalledRules object (exiting or new)
 *
 */
InstalledRule getInstalledRule(Session session, bytearray bearer) {

    // Session must be present
    if (session == null) {
        debug("getInstalledRule() missing session");
        return null;
    }

    // Find installed rule for bearer
    if (session.InstalledRules != null) {
        int i = 0;
        while (i < listSize(session.InstalledRules)) {
            InstalledRule item = listGet(session.InstalledRules, i);
            if (item.Bearer == bearer) {
                //debug("getInstalledRule() InstalledRule found = " + item);
                return item;
            }
            i = i + 1;
        }

    // Create new InstalledRules list inside session if missing
    } else {
        session.InstalledRules = listCreate(InstalledRule);
    }

    // Create new empty InstalledRule if not found matching in session
    InstalledRule installedRule = udrCreate(InstalledRule);
    installedRule.Bearer = bearer;
    installedRule.Rules = listCreate(int);
    listAdd(session.InstalledRules, installedRule);

    // Return new InstalledRule
    debug("getInstalledRule() new InstalledRule created = " + installedRule);
    return installedRule;
}