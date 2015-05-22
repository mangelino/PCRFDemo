/*
 * Module:                 PCRF_APL_Helpers 
 *
 * Date Created:           2012
 *
 * Author:                 DigitalRoute
 *
 * Purpose:                Functions for usage management handling
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
import ultra.Policy_Templates.PCRF_UFL_Internal;

import apl.Policy_Templates.PCRF_APL_Configuration;
import apl.Policy_Templates.PCRF_APL_Constants;
import apl.Policy_Templates.PCRF_APL_Functions;
import apl.Policy_Templates.PCRF_APL_Helpers;
import apl.Policy_Templates.PCRF_APL_User_Functions;


/*
 * Purpose:  Gx usage reporting - Commits all usage reported in CCR
 *          
 * Assumes:  Nothing
 *
 * Effects:  Nothing
 *
 * Comments: 
 *
 */
void commitUsageGx(rc rc) {
    debug("commitUsageGx() START");

    if (rc.ccr.umi == null || listSize(rc.ccr.umi) < 1) {
        debug("commitUsageGx() END Usage_Monitoring AVP not present or empty");
        return;
    }

    if (rc.bdh == null || mapSize(rc.bdh) < 1) {
        debug("commitUsageGx() ERROR Internal BDH list is empty");
        return;
    }

    // Commit usage for each BDH
    int i = 0;
    list<string> keys = mapKeys(rc.bdh);
    while (i < listSize(keys)) {
        string subscriberKey = listGet(keys, i);
        BucketDataHolder bdh = mapGet(rc.bdh, subscriberKey);
        debug("commitUsageGx() START BDH = " + subscriberKey);

        // Get notifications before usage commit
        list<Notification> notifications = getAllNotifications(bdh);

        // Commit usage for single BDH
        int j = 0;
        while (j < listSize(rc.ccr.umi)) {
            umi umi = listGet(rc.ccr.umi, j);
            debug("commitUsageGx() START Monitoring_Key = " + umi.monitoringKey);

            // Create counters list
            map<byte, long> counters = mapCreate(byte, long);
            mapSet(counters, INPUT, umi.input);
            mapSet(counters, OUTPUT, umi.output);
            mapSet(counters, TOTAL, umi.total);
            debug("commitUsageGx() USU = " + counters);

            // Get current session for BDH
            Session session = getSession(bdh, rc.ccr.Session_Id);

            // Commit usage for each reservation with same Monitoring-Key
            if (session != null && session.Reservations != null && listSize(session.Reservations) > 0) {
                int k = 0;
                while (k < listSize(session.Reservations)) {
                    Reservation r = listGet(session.Reservations, k);
                    if (r.Misc != null && mapContains(r.Misc, MISC_BUCKET_ID)
                    && (string)mapGet(r.Misc, MISC_MONITORING_KEY) == umi.monitoringKey) {

                        // Bucket ID from reservation
                        string bucketId = (string)mapGet(r.Misc, MISC_BUCKET_ID);
                        debug("commitUsageGx() reserved bucket = " + bucketId);

                        // Get bucket from BDH by bucket ID
                        Bucket bucket = getBucket(bdh.Buckets, bucketId);

                        // Commit usage into bucket
                        updateBucketCounters(bucket, counters, rc.errorCodes);

                        // Update User-Monitoring-Information item
                        if (bucket != null) {
                            if (umi.buckets == null) {
                                umi.buckets = listCreate(bucketMapping);
                            }
                            bucketMapping bucketMapping = udrCreate(bucketMapping);
                            bucketMapping.subscriberKey = subscriberKey;
                            bucketMapping.bucketId = bucket.ID;
                            listAdd(umi.buckets, bucketMapping);
                        }
                        debug("commitUsageGx() usage commited for bucket = " + bucketId);
                    }
                    k = k + 1;
                }
            }

            // Remove all reservations with Monitoring-Key, after usage commited
            removeReservation(session, umi.monitoringKey);

            debug("commitUsageGx() END Monitoring_Key = " + umi.monitoringKey);
            j = j + 1;
        }

        // Get notifications after usage commit and compare with notification before commit
        list<Notification> notificationsAfter = getAllNotifications(bdh);
        listRemoveExisting(notificationsAfter, notifications);

        // If new notifications found add to output list
        if (notificationsAfter != null && listSize(notificationsAfter) > 0) {
            j = 0;
            while (j < listSize(notificationsAfter)) {
                Notification n = listGet(notificationsAfter, j);
                NotificationInfo notification = udrCreate(NotificationInfo);
                notification.ID = n.ID;
                notification.Name = n.Name;
                notification.CounterType = n.CounterType;
                notification.Level = n.Level;
                notification.Required = n.Required;
                notification.Type = n.Type;
                notification.Address = n.Address;
                notification.Message = n.Message;
                notification.Misc = n.Misc;

                // Default recipient - subscriber key (IMSI or MSISDN)
                notification.recipient = rc.subscriberKey;

                // Group notification and Misc.Recipient exist
                if (subscriberKey != rc.subscriberKey && bdh.Subscriber != null
                && bdh.Subscriber.Misc != null && mapContains(bdh.Subscriber.Misc, MISC_RECIPIENT)) {
                    notification.recipient = (string)mapGet(bdh.Subscriber.Misc, MISC_RECIPIENT);
                }

                // Add same notification with same recipient only once for BDH
                listAddNoDup(rc.notifications, notification);
                j = j + 1;
            }
            debug("commitUsageGx() notifications after commit = " + listSize(rc.notifications));
        }
        //remove session and unlink memeber from group if flag is set in group session
        // TODO move to function unlinkMember(bdh, rc.bdh, rc.subscriberKey, rc.ccr.Session_Id)
        Session session = getSession(bdh, rc.ccr.Session_Id);
        if(session != null && session.Misc != null) {
            string memberToRemove = (string)mapGet(session.Misc, SESSION_MISC_RAR_REMOVE);
            if(memberToRemove != null) {
                debug("commitUsageGx() Group ID to remove = " + subscriberKey + "; Member to remove = " + memberToRemove);
                //remove member from group list, remove session
                removeMember(bdh, memberToRemove); 
                removeSession(bdh, rc.ccr.Session_Id);         
                //move groupp BDH to different container not to be used for rule selection
                if(rc.bdhRemoved == null) {
                    rc.bdhRemoved = mapCreate(string, BucketDataHolder);
                }
                mapSet(rc.bdhRemoved, subscriberKey, bdh);
                mapRemove(rc.bdh, subscriberKey);
                debug("commitUsageGx() Update group member list = " + mapGet(bdh.Subscriber.Misc, MISC_MEMBERS));
                //remove link from subscriber
                BucketDataHolder bdhMember = mapGet(rc.bdh, memberToRemove);
                if(bdhMember != null && bdhMember.Subscriber != null && bdhMember.Subscriber.Groups != null) {
                    int index = listFindIndex(bdhMember.Subscriber.Groups, k, k == subscriberKey);
                    debug("commitUsageGx() group index in member object to be removed = " + index);
                    if(index >= 0) {
                        listRemove(bdhMember.Subscriber.Groups, index);
                    }
                }
                
            }
        }         

        debug("commitUsageGx() END BDH = " + subscriberKey);
        i = i + 1;
    }
    debug("commitUsageGx() END");
}


/*
 * Purpose:  Grants quota over Gx
 *          
 * Assumes:  Nothing
 *
 * Effects:  Nothing
 *
 * Comments: 
 *
 */
void grantQuotaGx(rc rc) {

    debug("grantQuotaGx() START");

    // Missing BDH
    if (rc.bdh == null || mapSize(rc.bdh) < 1) {
        debug("grantQuotaGx() ERROR subscriber does not have buckets");
        return;
    }

    // Grant quota for CCR-I or CCR-U, never for CCR-T
    if (rc.ccr.CC_Request_Type != INITIAL_REQUEST
    && rc.ccr.CC_Request_Type != UPDATE_REQUEST) {
        debug("grantQuotaGx() ERROR usage reporting does not applies for CCR-T");
        return;
    }


    // Step 1
    // Create list of available Buckets and Monitoring-Keys for all BDHs
    list<bucketMapping> bucketsAll = getAllBuckets(rc);
    if (bucketsAll == null || listSize(bucketsAll) < 1) {
        debug("grantQuotaGx() ERROR missing active buckets");
        rc.cca.Result_Code = DIAMETER_UNABLE_TO_COMPLY;
        return;
    }


    // Step 2
    // In case of CCR-I usage for all available Monitoring-Keys will be granted
    // In case of CCR-U only for reported Monitoring-Keys usage will be granted
    // Buckets list for quota granting
    list<bucketMapping> buckets = listCreate(bucketMapping);

    // For CCR-I use all available buckets/Monitoring-Keys
    if (rc.ccr.CC_Request_Type == INITIAL_REQUEST) {
        buckets = bucketsAll;
        debug("grantQuotaGx() CCR-I - use all available buckets");

    // For CCR-U grant quota only for reported Monitoring-Keys
    } else if (rc.ccr.CC_Request_Type == UPDATE_REQUEST) {

        // If nothing reported in CCR-U then do not grant
        if (rc.ccr.umi == null || listSize(rc.ccr.umi) < 1) {
            debug("grantQuotaGx() ERROR For CCR-U missing reported Usage-Monitoring-Information");
            return;
        }

        // Create list of reported Monitoring-Keys that present in buckets list
        int j = 0;
        while (j < listSize(rc.ccr.umi)) {
            umi umi = listGet(rc.ccr.umi, j);

            // Check if Monitoring-Key is available in buckets list
            int k = 0;
            while (k < listSize(bucketsAll)) {
                bucketMapping item = listGet(bucketsAll, k);
                if (umi.monitoringKey == item.monitoringKey) {
                    listAdd(buckets, item);
                    debug("grantQuotaGx() for CCR-U Monitoring-Key [" + umi.monitoringKey + "] for bucket ["
                        + item.bucketId + "] and subscriber [" + item.subscriberKey + "]");
                }
                k = k + 1;
            }
            j = j + 1;
        }
    }

    // Bucket mapping is missing
    if (listSize(buckets) < 1) {
        debug("grantQuotaGx() ERROR Bucket mapping is missing");
        rc.cca.Result_Code = DIAMETER_UNABLE_TO_COMPLY;
        return;
    }


    // Sort by monitoring-Key
    // Necessary for correct reservations
    listSort(buckets, monitoringKey, ascending, bucketMapping);


    // Step 3
    // Grant quota
    int i = 0;
    map<string, umi> umi = mapCreate(string, umi);
    string lastKey = null;
    while (i < listSize(buckets)) {

        // Bucket and Monitoring-Key mapping
        bucketMapping item = listGet(buckets, i);
        debug("grantQuotaGx() START Monitoring_Key = " + item.monitoringKey + ", Bucket = " + item.bucketId + ", subscriberKey = " + item.subscriberKey);

        // Set reservations for Monitoring-Key
        // It is necessary to set reservations for previous Monitoring-Key
        if (lastKey != null && lastKey != item.monitoringKey) {
            debug("grantQuotaGx() set reservations for Monitoring-Key = " + lastKey);
            makeReservation(rc, umi, lastKey);
        }
        lastKey = item.monitoringKey;

        // Get BDH
        BucketDataHolder bdh = mapGet(rc.bdh, item.subscriberKey);

        // Get bucket
        Bucket bucket = getBucket(bdh.Buckets, item.bucketId);

        // Get session
        Session session = getSession(bdh, rc.ccr.Session_Id);

        // Data for quota grant present
        if (session != null && bucket != null) {

            // Get quota and set reservation
            umi gsu = getBucketQuota(bucket, session, bdh, item.monitoringKey, rc.errorCodes);

            // Usage_Monitoring_Information for CCA, if quota found
            if (gsu != null) {
                gsu.monitoringKey = item.monitoringKey;

                // Current Monitoring-Key is already added
                // Need to use smallest quota in CCR for each Monitoring-Key
                if (mapContains(umi, item.monitoringKey)) {
                    umi old = mapGet(umi, item.monitoringKey);
                    listAdd(old.buckets, item);
                    if ((gsu.input < old.input && gsu.input > 0) || old.input == 0) {
                        debug("grantQuotaGx() CC_Input_Octets: " + old.input + " -> " + gsu.input);
                        old.input = gsu.input;
                    }
                    if ((gsu.output < old.output && gsu.output > 0) || old.output == 0) {
                        debug("grantQuotaGx() CC_Output_Octets: " + old.output + " -> " + gsu.output);
                        old.output = gsu.output;
                    }
                    if ((gsu.total < old.total && gsu.total > 0) || old.total == 0) {
                        debug("grantQuotaGx() CC_Total_Octets: " + old.total + " -> " + gsu.total);
                        old.total = gsu.total;
                    }
                    debug("grantQuotaGx() update Monitoring-Key = " + item.monitoringKey);

                // Add new Monitoring-Key
                } else {
                    debug("grantQuotaGx() add Monitoring-Key = " + item.monitoringKey);
                    gsu.buckets = listCreate(bucketMapping, item);
                    mapSet(umi, item.monitoringKey, gsu);
                }

                debug("grantQuotaGx() quota granted for Monitoring-Key = " + item.monitoringKey);
            }
        } else {
            debug("grantQuotaGx() Session or Bucket missing");
        }

        debug("grantQuotaGx() END Monitoring_Key = " + item.monitoringKey);
        i = i + 1;
    }

    // Quota not granted
    // Set Result-Code = 5012
    // TODO what is subscriber reports final usage (bucket consumed), shall we return 5012 - error??? or 2001 without Usage-Monitoring-Information AVP?
    if (mapSize(umi) < 1) {
        rc.cca.Result_Code = DIAMETER_UNABLE_TO_COMPLY;
        debug("grantQuotaGx() ERROR quota not granted");
        return;
    }

    // Set reservations for last Monitoring-Key
    if (lastKey != null) {
        debug("grantQuotaGx() set reservations for last Monitoring-Key = " + lastKey);
        makeReservation(rc, umi, lastKey);
    }

    // Usage-Monitoring-Information in CCA
    rc.cca.umi = mapValues(umi);
    debug("grantQuotaGx() CCA Usage-Monitoring-Information = " + rc.cca.umi);
    debug("grantQuotaGx() END");
}


/*
 * Purpose:  Return map with BucketIDs and Monitoring-Keys for active buckets
 *          
 * Assumes:  Nothing
 *
 * Effects:  Nothing
 *
 * Comments:
 *
 */
list<bucketMapping> getAllBuckets(rc rc) {
    debug("getBuckets() START");

    // No buckets
    if (rc == null || rc.bdh == null || mapSize(rc.bdh) < 1) {
        debug("getBuckets() ERROR input is missing");
        return null;
    }

    // Get product mapping
    list<drudr> mapping = pccGetUdrList("PCC.Products.ProductMapping");

    // Sort mapping by priority
    listSort(mapping, Priority, ascending, ProductMapping);

    // Get list of all active products matching arguments
    list<bucketMapping> out = listCreate(bucketMapping);
    boolean stopFallthrough = false;
    int i = 0;
    while (i < listSize(mapping) && !stopFallthrough) {
        ProductMapping pm = (ProductMapping)listGet(mapping, i);

        // Monitoring-Key is present
        if (pm.Arguments != null && listSize(pm.Arguments) > 0) {

            // Monitoring-Key
            string key = listGet(pm.Arguments, 0);

            // Find products from targets list
            int j = 0;
            while (j < listSize(pm.Targets)) {
                Product p = listGet(pm.Targets, j);
                if (isProductActive(p.Periods, rc.timestamp)) {
                    bucketMapping item = getBucketByProduct(rc, p);
                    if (item != null) {
                        item.monitoringKey = key;

                        // Add to output list, skip duplicates
                        if (listAddNoDup(out, item)) {
                            debug("getBuckets() Added bucket = " + item.bucketId + ", product = " + p.ID
                                + ", Monitoring-Key = " + key + ", subscriberKey = " + item.subscriberKey);
                        }

                        // Check this flag only if valid bucket is found
                        if (p.StopFallthrough) {
                            debug("getBuckets() StopFallthrough for bucket = " + item.bucketId + " and product = " + p.ID);
                            stopFallthrough = p.StopFallthrough;
                        }
                    }
                }
                j = j + 1;
            }
        }
        i = i + 1;
    }

    // Valid buckets not found
    if (listSize(out) < 1) {
        debug("getBuckets() END - valid buckets not found");
        return null;
    }

    // Return buckets
    debug("getBuckets() END");
    return out;
}


/*
 * Purpose:  Returns active bucket for product, check buckets in BDH list
 *          
 * Assumes:  Nothing
 *
 * Effects:  Nothing
 *
 * Comments: 
 *
 */
bucketMapping getBucketByProduct(rc rc, Product product) {

    if (rc == null || rc.bdh == null || mapSize(rc.bdh) < 1 || product == null) {
        debug("getBucketByProduct() ERROR - missing input");
        return null;
    }

    // Check buckets in all BDHs
    Bucket bucket;
    string subscriber;
    int i = 0;
    list<string> keys = mapKeys(rc.bdh);
    while (i < listSize(keys)) {
        string subscriberKey = listGet(keys, i);
        BucketDataHolder bdh = mapGet(rc.bdh, subscriberKey);
        if (bdh.Buckets != null) {
            int j = 0;
            while (j < listSize(bdh.Buckets)) {
                Bucket b = listGet(bdh.Buckets, j);
                // Bucket matches product ID and is active
                if (b.Product == product.ID && isValidBucket(b, product, rc.timestamp)) {
                    // Compare buckets for same product
                    if (bucket == null || bucketEarliest(b, bucket)) {
                        bucket = b;
                        subscriber = subscriberKey;
                    }
                }
                j = j + 1;
            }
        }
        i = i + 1;
    }

    // Bucket not found
    if (bucket == null || subscriber == null) {
        return null;
    }

    // Create bucket mapping item
    bucketMapping item = udrCreate(bucketMapping);
    item.subscriberKey = subscriber;
    item.bucketId = bucket.ID;

    // Return bucket mapping
    debug("getBucketByProduct() bucket = " + bucket.ID + " found for product = " + product.ID);
    return item;
}


/*
 * Purpose:  Update single bucket usage.
 *          
 * Assumes:  Nothing
 *
 * Effects:  Nothing
 *
 * Comments: Unlimited product is product with flag StopAtCapacity set to FALSE
 *           Limited product is product with flag StopAtCapacity set to TRUE
 *
 */
boolean updateBucketCounters(Bucket b, map<byte, long> counters, list<int> errorCodes) {
    debug("updateBucketCounters() START");

    // Bucket missing
    if (b == null) {
        debug("updateBucketCounters() ERROR - missing bucket");
        return false;
    }

    // Counters missing
    if (counters == null || mapSize(counters) < 0) {
        debug("updateBucketCounters() ERROR - missing counters");
        if(errorCodes != null) {
           listAdd(errorCodes, ERR_LOG_MISSING_COUNTERS);
        }
        return false;
    }

    // Get product
    Product p = (Product)pccGetUdr("PCC.Products.Product", b.Product);
    if (p == null) {
        debug("updateBucketCounters() ERROR - product not found");
        if(errorCodes != null) {
           listAdd(errorCodes, ERR_LOG_PRODUCT_NOT_FOUND);
        }
        return false;
    }

    //if external_usage_control is enabled, do not update bucket coutners
    if(p.Misc != null && mapGet(p.Misc, MISC_PROD_EXT_USAGE_CTRL) != null) {
        boolean isExtUSageCount = (boolean)mapGet(p.Misc, MISC_PROD_EXT_USAGE_CTRL);
        debug("updateBucketCounters() External_Usage_Flag = " +  isExtUSageCount + "; for bucket = " + b.ID);
        if(isExtUSageCount) {
            return false;
        }
        
    }

    // Get bucket counter
    Counter counter = getBucketCounter(b);

    // Create new bucket counter if missing
    if (counter == null) {
        counter = udrCreate(Counter);
        b.Counters = listCreate(Counter, counter);
    }

    // Create new usage inside buckt counter
    if (counter.Usage == null) {
        counter.Usage = mapCreate(byte, long);
    }

    // Commit all reported usage in bucket
    int i = 0;
    list<byte> keys = mapKeys(counters);
    while (i < listSize(keys)) {
        // Usage
        byte counterType = listGet(keys, i);
        long usage = mapGet(counters, counterType);
        long value = mapGet(counter.Usage, counterType);

        // Skip if nothing to commit
        if (usage > 0) {
            debug("updateBucketCounters() bucket = " + b.ID + ", counterType = " + counterType + ", reported usage = "
                + usage + ", bucket usage = " + value + ", new usage = " + (value + usage));
            value = value + usage;
            mapSet(counter.Usage, counterType, value);
        }
        i = i + 1;
    }

    debug("updateBucketCounters() END");
    return true;
}


/*
 * Purpose:  Get Granted-Service-Units for bucket.
 *          
 * Assumes:  Nothing
 *
 * Effects:  Nothing
 *
 * Comments: 
 *
 */
umi getBucketQuota(Bucket bucket, Session session, BucketDataHolder bdh, string monitoringKey, list<int> errorCodes) {
    debug("getBucketQuota() START");

    // Missing bucket
    if (bucket == null) {
        debug("getBucketQuota() ERROR - missing input");
        return null;
    }

    // Get product
    Product p = (Product)pccGetUdr("PCC.Products.Product", bucket.Product);
    if (p == null) {
        debug("getBucketQuota() ERROR - product not found for bucket = " + bucket.ID);
        if(errorCodes != null) {
           listAdd(errorCodes, ERR_LOG_PRODUCT_NOT_FOUND);
        }
        return null;
    }

    // Get product capacities, in case product has mutiple capacities with same counterType then take biggest one
    map<byte, Capacity> capacities = getProductCapacities(p.Capacities);

    // Missing capacities - nothing to grant
    // Capacities contains quota size
    if (capacities == null || mapSize(capacities) < 0) {
        debug("getBucketQuota() ERROR - capacities missing for product = " + p.ID);
        if(errorCodes != null) {
           listAdd(errorCodes, ERR_LOG_MISSING_CAPACITIES);
        }
        return null;
    }            

    // GSU
    umi out = udrCreate(umi);

    // Get existing reservations, accross all sessions
    map<byte, long> reservation = mapCreate(byte, long);
    reservation = getReservedUnits(bdh, null, bucket.ID);

    // Get used units from bucket
    Counter counter = getBucketCounter(bucket);

    debug("getBucketQuota() reservation  = " + reservation);
    debug("getBucketQuota() usage  = " + counter.Usage);
    debug("getBucketQuota() capacity keys  = " + mapKeys(capacities));

    // CC_Input_Octets
    if (mapContains(capacities, (byte)INPUT)) {
        Capacity c = mapGet(capacities, INPUT);
        out.input = calculateQuota(c, counter.Usage, reservation, p.StopAtCapacity);
    }

    // CC_Output_Octets
    if (mapContains(capacities, OUTPUT)) {
        Capacity c = mapGet(capacities, OUTPUT);
        out.output = calculateQuota(c, counter.Usage, reservation, p.StopAtCapacity);
    }

    // CC_Total_Octets
    if (mapContains(capacities, TOTAL)) {
        Capacity c = mapGet(capacities, TOTAL);
        out.total = calculateQuota(c, counter.Usage, reservation, p.StopAtCapacity);
    }

    // Return granted units
    debug("getBucketQuota() END");
    return out;
}


/*
 * Purpose:  Calculate quota to grant.
 *          
 * Assumes:  Nothing
 *
 * Effects:  Nothing
 *
 * Comments: 
 *
 */
long calculateQuota(Capacity c, map<byte, long> usage, map<byte, long> reservation, boolean stopAtCapacity) {
    debug("calculateQuota() START");
    if (c == null) {
        debug("calculateQuota() ERROR - missing input");
        return 0;
    }

    // For unlimited product always grant default quota
    if (!stopAtCapacity) {
        debug("calculateQuota() END - stopAtCapacity=false - grant defaultQuota = " + c.QuotaDefault);
        return c.QuotaDefault;
    }

    // Max usage
    long capacity = convertToBytes(c.Capacity, c.CapacityUnit);

    // Reserved units
    long reserved = 0;
    if (reservation != null && mapContains(reservation, c.CounterType)) {
        reserved = mapGet(reservation, c.CounterType);
    }

    // Used units
    long used = 0;
    if (usage != null && mapContains(usage, c.CounterType)) {
        used = mapGet(usage, c.CounterType);
    }

    // Left amount in bucket
    long leftAmount = capacity - used - reserved;

    debug("calculateQuota() used = " + used + ", reserved = " + reserved + ", capacity = " + capacity
        + ", left = " + leftAmount + ", QuotaDefault = " + c.QuotaDefault + ", QuotaMinimum = " + c.QuotaMinimum);

    // Grant default quota
    if (leftAmount > c.QuotaDefault) {
        debug("calculateQuota() END - grant defaultQuota = " + c.QuotaDefault);
        return c.QuotaDefault;
    }

    // Grant min-quota
    if (leftAmount > c.QuotaMinimum) {
        debug("calculateQuota() END - grant minQuota = " + c.QuotaMinimum);
        return c.QuotaMinimum;
    }

    // Grant less than min-quota
    if (leftAmount > 0) {
        debug("calculateQuota() END - grant less than minQuota = " + leftAmount);
        return leftAmount;
    }

    // Bucket used
    debug("calculateQuota() END nothing to grant");
    return 0;
}


/*
 * Purpose:  Make reservation for Monitoring-Key, same quota for all buckets
 *          
 * Assumes:  Nothing
 *
 * Effects:  Nothing
 *
 * Comments: 
 *
 */
void makeReservation(rc rc, map<string, umi> umiList, string monitoringKey) {
    debug("makeReservation() START");

    // Missing input
    if (rc == null || rc.bdh == null || mapSize(rc.bdh) < 1
    || umiList == null || mapSize(umiList) < 1 || monitoringKey == null
    || !mapContains(umiList, monitoringKey)) {
        debug("makeReservation() ERROR - missing input");
        return;
    }

    // Get UMI item
    umi umi = mapGet(umiList, monitoringKey);
    if (umi.buckets == null || listSize(umi.buckets) < 1) {
        debug("makeReservation() ERROR - no buckets in UMI = " + umi);
        return;
    }

    // Granted units
    map<byte, long> granted = mapCreate(byte, long);
    if (umi.input > 0) {
        mapSet(granted, INPUT, umi.input);
    }
    if (umi.output > 0) {
        mapSet(granted, OUTPUT, umi.output);
    }
    if (umi.total > 0) {
        mapSet(granted, TOTAL, umi.total);
    }

    // Nothing to grant
    if (mapSize(granted) < 1) {
        debug("makeReservation() ERROR - nothing to grant for UMI = " + umi);
        return;
    }

    // Set reservations
    int i = 0;
    while (i < listSize(umi.buckets)) {

        // Bucket maping for reservation
        bucketMapping item = listGet(umi.buckets, i);

        // Get BDH
        BucketDataHolder bdh = mapGet(rc.bdh, item.subscriberKey);

        // Get session
        Session session = getSession(bdh, rc.ccr.Session_Id);

        // Set reservation for session
        if (mapSize(granted) > 0 && session != null) {
            debug("makeReservation() set reservation for monitoringKey = " + item.monitoringKey + ", bucketId = " + item.bucketId
                + ", subscriber = " + item.subscriberKey);
            setReservation(session, item.monitoringKey, item.bucketId, granted);
        }

        i = i + 1;
    }

    debug("makeReservation() END");
}


/*
 * Purpose:  Return all matching notifications for subscriber
 *           Notification shall be set to Required or subscriber shall be subscribed for notification
 *          
 * Assumes:  Nothing
 *
 * Effects:  Nothing
 *
 * Comments: 
 *
 */
list<Notification> getAllNotifications(BucketDataHolder bdh) {
    debug("getAllNotifications() START");

    // Missing buckets
    if (bdh == null || bdh.Buckets == null || listSize(bdh.Buckets) < 1) {
        debug("getAllNotifications() ERROR missing input");
        return null;
    }

    // Calculate notifications from buckets
    list<Notification> notifications = listCreate(Notification);
    int i = 0;
    while (i < listSize(bdh.Buckets)) {
        Bucket b = listGet(bdh.Buckets, i);
        Product p = (Product)pccGetUdr("PCC.Products.Product", b.Product);
        Counter c = null;
        debug("getAllNotifications() bucket = " + b.ID + ", product = " + b.Product);

        // Check if product, capacities, counters and notifications are present
        if (p != null && p.Notifications != null && listSize(p.Notifications) > 0
        && p.Capacities != null && listSize(p.Capacities) > 0) {
            c = getBucketCounter(b);
        }

        // Counter found - compare counters with capacities
        if (c != null) {

            // Check all counterTypes for bucket
            int j = 0;
            list<byte> keys = mapKeys(c.Usage);
            while (j < listSize(keys)) {

                // CounterType and usage for counterType
                byte counterType = listGet(keys, j);
                long usage = mapGet(c.Usage, counterType);

                // Check all product notifications
                int k = 0;
                while (k < listSize(p.Notifications)) {
                    Notification n = listGet(p.Notifications, k);

                    // Use notification with same counterType as usage
                    if (n.CounterType == counterType) {
                        long capacity = 0;

                        // Get capacity for usage counterType
                        Capacity cy = getCapacityByType(p.Capacities, counterType);
                        if (cy != null) {
                            capacity = convertToBytes(cy.Capacity, cy.CapacityUnit);
                        }

                        // Send Notifications
                        // No notifications if capacity set to unlimited (0) or if there is no capacity for counterType
                        if (capacity > 0) {
// TODO if capacity is 0 then its OK to have notification level as absolute value (bigger than 1)
// this is necessary to allow notifications for unlimited products

                            // If notification level is 1 or less then its percentage
                            // If notification level above 1 then its absolute value in bytes 
                            long level = 0;
                            if (n.Level <= 1) {
                                level = (long)(capacity * n.Level);
                            } else {
                                level = (long)n.Level;
                            }

                            // Handle first usage notification
                            // Used counter value bigger than notification level
                            boolean notificationTriggered = false;
                            if (level == 0 && usage > level) {
                                notificationTriggered = true;

                            // Normal notification
                            // Used counter value equal or bigger than notification level
                            } else if (level > 0 && usage >= level) {
                                notificationTriggered = true;
                            }

                            debug("getAllNotifications() level = " + level + ", usage = " + usage
                                + ", counterType = " + counterType + ", capacity = " + capacity
                                + ", notification = " + n.Name + ", triggered = " + notificationTriggered);

                            // If Required flag set, then send notification for all subscribers
                            if (notificationTriggered && n.Required) {
                                listAddNoDup(notifications, n);
                                debug("getAllNotifications() notification [" + n.Name + "] added as Required");
                                

                            // Check if subscriber is subscribed for non Required notification
                            } else if (notificationTriggered && bdh.Subscriber != null
                            && bdh.Subscriber.Notifications != null && listSize(bdh.Subscriber.Notifications) > 0) {
                                int l = 0;
                                while (l < listSize(bdh.Subscriber.Notifications)) {
                                    // If subscriber has subscribed for non Required notification
                                    if (listGet(bdh.Subscriber.Notifications, l) == n.ID) {
                                        listAddNoDup(notifications, n);
                                        debug("getAllNotifications() notification [" + n.Name + "] added as Subscribed");
                                    }
                                    l = l + 1;
                                }
                            }
                        }
                    }
                    k = k + 1;
                }
                j = j + 1;
            }
        }
        i = i + 1;
    }
    debug("getAllNotifications() END notifications found = " + listSize(notifications));

    return notifications;
}

