string formatHtml(RequestCycleUDR udr, string action){
//debug("formatHTML");
    
    any txn = pccBeginBucketDataTransaction ();

    BucketDataHolder bdh = pccBucketDataLookup(mapGet(requestValues, KEY_IDENTITY), txn);

    if (action== "Refresh") {
        int index = 0;
        list<string> mk = listCreate(string);

        while (index < nbOfMonitoringKey) {
            listAdd(mk, (string)mapGet(requestValues, "mk"+index+"Name"));
            index = index + 1;
        }

        // Monitoring keys loop
        index = 0;

        while (index < listSize(mk)) {
            ret = ret + "    <tr>";
            string mkName = listGet(mk, index);
            string grantedValue = "0"; 
            index = index + 1; 
        }
    }

        

    if (udr != null) {
        list<string> mk = getMonitoringKey(udr);

        if (listSize(mk) < nbOfMonitoringKey) {

            int index = 0;
            int temp = 0;
            boolean toBeAdded = true;

            while (index < nbOfMonitoringKey) {

                if (temp < listSize (mk)) {
                    if ((string)mapGet(requestValues, "mk"+index+"Name") == listGet(mk, temp)) {
                        temp = listSize (mk);
                        toBeAdded = false;
                    }
                    temp = temp + 1;
                }

                if (toBeAdded) {
                    debug("requestValues: " + requestValues);
                    debug("mkIndexName: " + (string)mapGet(requestValues, "mk"+index+"Name"));
                    listAdd(mk, (string)mapGet(requestValues, "mk"+index+"Name"));
                }
                toBeAdded = true;
                index = index + 1;
            }    
        }

        // Monitoring keys loop
        int index = 0;
        debug("mk: " + mk);

        while (nbOfMonitoringKey < listSize(mk)) {
            updateMkNumber( nbOfMonitoringKey + 1);
        }

        while (index < listSize(mk)) {
            ret = ret + "    <tr>";
            string mkName = listGet(mk, index);
            string grantedValue = "0"; 
            grantedValue = (string) getGrantedValue(udr, mkName);
            index = index + 1; 
        }

        list<string> installedRules = getInstalledRules(udr);
        list<string> removedRules = getRemovedRules(udr);



/*Buckets and consumption*/

 
        if (bdh != null) {

            index = 0;

            while(bdh.Buckets != null && index < listSize(bdh.Buckets)) {
                Bucket current = listGet(bdh.Buckets, index);
                long value = 0;

                if (current.Counters != null && listSize(current.Counters) >0) {
                    value = mapGet(listGet(current.Counters, 0).Usage,2);
                }

                Product prod = (Product)pccGetUdr("PCC.Products.Product", current.Product);
              index = index + 1;        
            }
            ret = ret + "     </table>";
        }


/*END Buckets and consumption*/


        if(listSize(installedRules)>0 || listSize(removedRules)>0) {

            int ruleIndex = 0;

            while (ruleIndex < listSize(installedRules) || ruleIndex < listSize(removedRules)) {

                ruleIndex = ruleIndex + 1;
            }

        } // End rule part

        if(instanceOf(udr.Answer, CC_Answer) && ((CC_Answer)udr.Answer).Error_Message != null) {
        }

    } // end ccr!=null

 
 

    list<string> rulesNameList = getInstalledRulesNames(bdh);
 
    if (rulesNameList != null && listSize(rulesNameList ) >0) {
        int index = 0;

        while(index < listSize(rulesNameList)) {
            index = index + 1;        
        }
    }

 
    pccBucketDataStore(mapGet(requestValues, KEY_IDENTITY), bdh, txn);
    pccCommitBucketDataTransaction(txn);
   
    return ret;
}
