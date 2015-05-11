string formatHtml(RequestCycleUDR udr, string action){
//debug("formatHTML");
    string ret = "";
  
    any txn = pccBeginBucketDataTransaction ();

    BucketDataHolder bdh = pccBucketDataLookup(mapGet(requestValues, KEY_IDENTITY), txn);

    debug("nbOfMonitoringKey: " + nbOfMonitoringKey);
    if (action== "Refresh") {
        ret = ret + "    <section>";
        ret = ret + "        <h2>Monitoring Keys</h2>";
        ret = ret + "          <table border=\"0\" class=\"contentTable\">";
        
        int index = 0;
        list<string> mk = listCreate(string);

        while (index < nbOfMonitoringKey) {
            debug("mk: " + (string)mapGet(requestValues, "mk0Name"));
            debug("mk: " + (string)mapGet(requestValues, "mk1Name"));
            listAdd(mk, (string)mapGet(requestValues, "mk"+index+"Name"));
            index = index + 1;
            debug("index: " + index);
            debug("nbOfMonitoringKey: " + nbOfMonitoringKey);
        }

        debug("mk: " + mk);
        // Monitoring keys loop
        index = 0;

        while (index < listSize(mk)) {
            ret = ret + "    <tr>";
            string mkName = listGet(mk, index);
            string grantedValue = "0"; 

            ret = ret + "      <th scope=\"row\">"+index+" Name:</th>";
            ret = ret + "      <td><input type=\"text\" name=\"mk"+index+"Name\" value=\""+mkName+"\"/> </td>";

            ret = ret + "      <th scope=\"row\">GSU: </th>";
            ret = ret + "      <td>"+grantedValue+"</td>";
            ret = ret + "      <th scope=\"row\">USU</th>";
            ret = ret + "      <td><input type=\"text\" name=\"mk"+index+"Value\" value=\"\"/> </td>";
            ret = ret + "    </tr>";

            index = index + 1; 
        }

      

    }

        

    if (udr != null) {
        ret = ret + "    <section>";
        ret = ret + "        <h2>Monitoring Keys</h2>";
        ret = ret + "          <table border=\"0\" class=\"contentTable\">";

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

            //ret = ret + "      <th scope=\"row\">"+index+" Name:</th>";
            ret = ret + "      <th scope=\"row\">Name:</th>";
            ret = ret + "      <td><input type=\"text\" name=\"mk"+index+"Name\" value=\""+mkName+"\"/> </td>";

            ret = ret + "      <th scope=\"row\">GSU: </th>";
            ret = ret + "      <td>"+grantedValue+"</td>";
            ret = ret + "      <th scope=\"row\">USU</th>";
            ret = ret + "      <td><input type=\"text\" name=\"mk"+index+"Value\" value=\"\"/> </td>";
            ret = ret + "    </tr>";

            index = index + 1; 
        }

        ret = ret + "    </table>";
        ret = ret + "      <p>&nbsp;</p>";
        ret = ret + "    </section>";

        ret = ret + "    <section>";
        ret = ret + "     <h2>Results</h2>";
        list<string> installedRules = getInstalledRules(udr);
        list<string> removedRules = getRemovedRules(udr);



/*Buckets and consumption*/

        ret = ret + "     <table border=\"0\" class=\"contentTable\"><tr><th>Product Name</th><th>Consumption</th></tr>";

        if (bdh != null) {

            index = 0;
            
            while(bdh.Buckets != null && index < listSize(bdh.Buckets)) {
                Bucket current = listGet(bdh.Buckets, index);
                long value = 0;

                if (current.Counters != null && listSize(current.Counters) >0) {
                    value = mapGet(listGet(current.Counters, 0).Usage,2);
                }

                Product prod = (Product)pccGetUdr("PCC.Products.Product", current.Product);

                ret = ret + "    <tr><td><span style=\"color: black;\">";
                ret = ret + prod.Name;

                ret = ret + "</span></td><td><span style=\"color: black;\">";
                ret = ret +value;


                ret = ret + "</span></td></tr>";
                index = index + 1;        
            }
            ret = ret + "     </table>";
        }


/*END Buckets and consumption*/


        ret = ret + "     <table border=\"0\" class=\"contentTable\"><tr><th>Rules to install</th><th>Rules to Remove</th></tr>";

        if(listSize(installedRules)>0 || listSize(removedRules)>0) {

            int ruleIndex = 0;

            while (ruleIndex < listSize(installedRules) || ruleIndex < listSize(removedRules)) {
                ret = ret + "    <tr><td><span style=\"color: green;\">";

                if(ruleIndex < listSize(installedRules)) {

                    ret = ret + listGet(installedRules, ruleIndex);
                }
                else {
                    ret = ret + "&nbsp;";
                }

                ret = ret + "</span></td><td><span style=\"color: red;\">";

                if(ruleIndex < listSize(removedRules)) {
                    ret = ret + listGet(removedRules, ruleIndex);
                }
                else {
                    ret = ret + "&nbsp;";
                }
                ret = ret + "</span></td></tr>";
                ruleIndex = ruleIndex + 1;
            }

        } // End rule part
            ret = ret + "     </table>";

        ret = ret + "     <h4>Request</h4>";
        ret = ret + "     <p class=\"codage\">"+udr.Request+"</p>    ";
        ret = ret + "     <h4>Answer</h4>";

        if(instanceOf(udr.Answer, CC_Answer) && ((CC_Answer)udr.Answer).Error_Message != null) {
            ret = ret + "          <p>"+((CC_Answer)udr.Answer).Error_Message+"</p>";
        }

        ret = ret + "          <p class=\"codage\">"+udr.Answer+"</p>";
        ret = ret + "    </section>";
    } // end ccr!=null

 
    ret = ret + "  <!-- end .content --></article>";
    ret = ret + "  <aside>";
    ret = ret + "    <ul class=\"nav\">";
    ret = ret + "    </ul>";
    //ret = ret + "    <p>&nbsp;</p>";


    list<string> rulesNameList = getInstalledRulesNames(bdh);
    ret = ret + "    <h3>Installed Rules:</h3>";

    if (rulesNameList != null && listSize(rulesNameList ) >0) {
        int index = 0;

        while(index < listSize(rulesNameList)) {
            ret = ret + "   <p>" + listGet(rulesNameList, index) +"</p>";
            index = index + 1;        
        }
    }

    ret = ret + "  </aside>";
    ret = ret + "  </form>";
    ret = ret + "  <footer>";
    ret = ret + "    <p>Copyright DigitalRoute 2012.</p>";
    ret = ret + "    <address>";
    ret = ret + "    </address>";
    ret = ret + "  </footer>";
    ret = ret + "  <!-- end .container --></div>";
    ret = ret + "</body>";
    ret = ret + "</html>";

    pccBucketDataStore(mapGet(requestValues, KEY_IDENTITY), bdh, txn);
    pccCommitBucketDataTransaction(txn);
    return ret;
}