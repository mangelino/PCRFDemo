var intervalId = [];
	var consChart = [];
	var bwChart = [];
	var consDps = [];
	var bwDps = []; // dataPoints
	var consumed = [];
	var tempConsumed = [];
	var MAXSTOP = 999999999;
	var AVGBW = 500000;
	var THROTTLE = [];
	var REPORT_THRESHOLD = [];
	var pcefRules;

	{% for minfo in session.monitoringInfo.values() %}
		consDps["{{minfo.key}}"] = [];
		bwDps["{{minfo.key}}"] = [];
		THROTTLE["{{minfo.key}}"] = 999999999;
		REPORT_THRESHOLD["{{minfo.key}}"] = {{minfo.gsu}};
	{% endfor %}

	// Lookup dictionary for the mapping between PCC Rules and monitoringKey
	var minfoKeys = [];
	minfoKeys["Data"] = 1;
	minfoKeys["Turbo"] = 1;
	minfoKeys["Throttle"] = 1;
	minfoKeys["Throttle_Group"] = 1;
	minfoKeys["Youtube"] = 2;
	minfoKeys["SportVOD"] = 3;

	window.onload = function() {
		{% for minfo in session.monitoringInfo.values() %}
		consChart["{{minfo.key}}"] = new CanvasJS.Chart("consumption_{{minfo.key}}",{
			title :{
				text: "Data consumption"
			},			
			data: [{
				type: "line",
				dataPoints: consDps["{{minfo.key}}"]
			}]
		});

		bwChart["{{minfo.key}}"] = new CanvasJS.Chart("bandwidth_{{minfo.key}}",{
			title :{
				text: "Bandwidth"
			},			
			data: [{
				type: "line",
				dataPoints: bwDps["{{minfo.key}}"]
			}]
		});
		{% endfor %}

		$.ajax(
			    {
			        url : "/pcef/{{pcef.id}}/rules/json",
			        type: "GET",
			        data : null,
			        success:function(data, textStatus, jqXHR) 
			        {
			        	pcefRules = JSON.parse(data);
			        },
			        error: function(jqXHR, textStatus, errorThrown) 
			        {
			            alert(textStatus);      
			        }
			    });


	}



	var xVal = [];
	var stopX = MAXSTOP;	
	var averageBw = 20000;
	var updateInterval = 20;
	var dataLength = 500; // number of dataPoints visible at any point

	function updateChart (count, bw, monitoringKey) {
		var yVal;
		count = count || 1;
		// count is number of times loop runs to generate random dataPoints.
		var delta= Math.round(bw/5 + Math.random() *(-bw));
		if (xVal[monitoringKey] === undefined) {
			xVal[monitoringKey] = 0;
		}
		if (consDps[monitoringKey] === undefined) {
			consDps[monitoringKey] = [];
		}

		if (bwDps[monitoringKey] === undefined) {
			bwDps[monitoringKey] = [];
		}

		if (tempConsumed[monitoringKey] === undefined) {
			tempConsumed[monitoringKey] = 0;
		}

		if (consumed[monitoringKey] === undefined) {
			consumed[monitoringKey] = 0;
		}
		for (var j = 0; j < count; j++) {	
			yVal = bw +  delta;

			if (yVal > THROTTLE[monitoringKey]) {
				yVal = THROTTLE[monitoringKey];

			}

			if (yVal<0) {
				yVal = 0;
			}
			bwDps[monitoringKey].push({
				x: xVal[monitoringKey],
				y: yVal
			});

			consumed[monitoringKey] = consumed[monitoringKey] + yVal;
			tempConsumed[monitoringKey] = tempConsumed[monitoringKey] + yVal;
			consDps[monitoringKey].push({
				x: xVal[monitoringKey],
				y: consumed[monitoringKey]
			});

			xVal[monitoringKey]++;

		};
		if (bwDps[monitoringKey].length > dataLength)
		{
			bwDps[monitoringKey].shift();
		}

		if (consDps[monitoringKey].length > dataLength)
		{
			consDps[monitoringKey].shift();
		}
		consChart[monitoringKey].render();
		bwChart[monitoringKey].render();

		if (tempConsumed[monitoringKey] > REPORT_THRESHOLD[monitoringKey]) {
			submitFormPredefined(monitoringKey,tempConsumed[monitoringKey], monitoringKey);
			tempConsumed[monitoringKey] = 0;
		}
	};
	

	function start(key) {
		stopX = MAXSTOP;
		$("#usageTable_"+key).hide();
		if (intervalId[key]) {
			clearInterval(intervalId[key]);
		}
		// generates first set of dataPoints
		updateChart(dataLength,0, key);
		//consumed = 0;

		// update chart after specified time. 
		intervalId[key] = setInterval(function(){updateChart(1, AVGBW, key);}, updateInterval);
	}

	function stop(key) {
		// update chart after specified time. 
		if (intervalId[key]) {
			clearInterval(intervalId[key]);
		}
		$("#usageTable_"+key).show();
	}

	function pause(key) {
		if (intervalId[key]) {
			clearInterval(intervalId[key]);
			intervalId[key] = null;
			$("#usageTable_"+key).show();
		} else {
			$("#usageTable_"+key).hide();
			intervalId[key] = setInterval(function(){updateChart(1, AVGBW, key);}, updateInterval);
		}
		
	}

	function submitFormPredefined(elem_id, bytes, key)
	{
		document.getElementById(elem_id).value = bytes; 
		var postData = $("#sessionForm").serializeArray();
    	var formURL = $("#sessionForm").attr("altaction");
		$.ajax(
			    {
			        url : formURL,
			        type: "POST",
			        data : postData,
			        success:function(data, textStatus, jqXHR) 
			        {
						document.getElementById(elem_id).value = "";
			        	var jsondata = JSON.parse(data);
			            //alert(data);//data: return data from server

			            bucketRows = "";
			            for (var j = 0; j < jsondata.buckets.length; j++) {
			            	//$("#bucket_"+jsondata.buckets[j].id).html(getReadableFileSizeString(jsondata.buckets[j].counters.tot));
			            	bucketRows += generateBucketRow(jsondata.buckets[j]);

			            }
			            $("#bucketsTable tbody").html(bucketRows);
			            for (var minfoKey in jsondata.session.monitoringInfo) {
			            	$("#mkey_"+minfoKey).html(getReadableFileSizeString(jsondata.session.monitoringInfo[minfoKey].usu));
			            	REPORT_THRESHOLD[minfoKey] = jsondata.session.monitoringInfo[minfoKey].gsu

			            }
			            var rules = jsondata.session.rules;
			            rulesHtml = "";
			            for (var j=0; j<rules.length; j++) {
			            	rulesHtml += '<span class="label label-primary">'+rules[j]+'</span>'
			            	// This is an hack. The usage is monitored on the monitoringInfoKey, but the 
			            	// QoS is set on the PCC Rule, and there is no guarantee that they will apply to the
			            	// same traffic. In the demo we want to show that the QoS is applied to the traffic
			            	// matching the monitporing key, which is what we show in the Real Time graphs
			            	if (jsondata.session.qosInfo != null) {
				            	THROTTLE[minfoKeys[rules[j]]] = jsondata.session.qosInfo.MBR_DL;
				            } else {
				            	THROTTLE[minfoKeys[rules[j]]] = Math.min(THROTTLE[minfoKeys[rules[j]]], jsondata.pcef.staticRules[rules[j]].qosInfo.MBR_DL);
				            }
			            }

			            $("#rules").html(rulesHtml);

			        },
			        error: function(jqXHR, textStatus, errorThrown) 
			        {
			            //if fails      
			        }
			    });
	}

	function generateBucketRow(bucket)
	{
		c = "";
		if (checkValidity(bucket.stopTime)) {
			c += '<tr>\n';
			c += "<td>"+bucket.id+"</td>";
			c += "<td>"+bucket.name+"</td>";
			// c += "<td>"+bucket.startTime+"</td>";
			// c += "<td>"+bucket.stopTime+"</td>";
			c += "<td>"+getReadableFileSizeString(bucket.counters.tot)+"</td>";
			c += "</tr>";
		}
		return c;
	}

	function checkValidity(time)
	{
		var now = new Date();
		if (Date.parse(time)<now.setSeconds(now.getSeconds()-60)) {
			return false;
		} else {
			return true;
		}
	}

	function getReadableFileSizeString(fileSizeInBytes) {

	    var i = -1;
	    var byteUnits = [' kB', ' MB', ' GB', ' TB', 'PB', 'EB', 'ZB', 'YB'];
	    do {
	        fileSizeInBytes = fileSizeInBytes / 1024;
	        i++;
	    } while (fileSizeInBytes > 1024);

	    return Math.max(fileSizeInBytes, 0.1).toFixed(1) + byteUnits[i];
	};

	function toggleLiveTraffic(key) {
		$("#expandicon_"+key).toggleClass("glyphicon-expand glyphicon-collapse-up");
		$("#livetraffic_"+key).toggleClass("hidden");
	};