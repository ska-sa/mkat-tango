package com.tango.nodes.simulators;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Random; 
import java.util.Set;   
import java.util.Iterator;
import org.json.simple.JSONArray;
import org.json.simple.JSONObject;
import org.json.simple.JSONValue;
import fr.esrf.Tango.DevFailed;
import fr.esrf.TangoApi.DeviceAttribute;
import fr.esrf.TangoApi.DeviceProxy;
  
public class WeatherSimulator_CNSimulator {
	String parseResponse = "{\"RESET\":[{\"RES_RESET\":[{\"allowedValues\":\"0,\",\"minValue\":\"0\",\"maxValue\":\"0\",\"parameterName\":\"msg\",\"value\":\"0\"}]}],\"OFF\":[{\"RES_OFF\":[{\"allowedValues\":\"0,\",\"minValue\":\"0\",\"maxValue\":\"0\",\"parameterName\":\"msg\",\"value\":\"0\"}]}],\"ON\":[{\"RES_ON\":[{\"allowedValues\":\"0,\",\"minValue\":\"0\",\"maxValue\":\"0\",\"parameterName\":\"msg\",\"value\":\"0\"}]}]}";
		String parseDataPoint = "{\"Temperature\":{\"allowedValues\":\"0,\",\"minValue\":\"-10\",\"maxValue\":\"55\",\"skipSteps\":3,\"waveForm\":\"sine\",\"timeLag\":100,\"value\":25},\"Wind_Direction\":{\"allowedValues\":\"0,\",\"minValue\":\"0\",\"maxValue\":\"360\",\"skipSteps\":3,\"waveForm\":\"sine\",\"timeLag\":100,\"value\":60},\"Insolation\":{\"allowedValues\":\"0,\",\"minValue\":\"0\",\"maxValue\":\"1200\",\"skipSteps\":3,\"waveForm\":\"sine\",\"timeLag\":100,\"value\":500},\"Rainfall\":{\"allowedValues\":\"0,\",\"minValue\":\"0\",\"maxValue\":\"4\",\"skipSteps\":3,\"waveForm\":\"sine\",\"timeLag\":100,\"value\":1},\"Wind_Speed\":{\"allowedValues\":\"0,\",\"minValue\":\"0\",\"maxValue\":\"30\",\"skipSteps\":3,\"waveForm\":\"sine\",\"timeLag\":100,\"value\":10},\"Pressure\":{\"allowedValues\":\"0,\",\"minValue\":\"500\",\"maxValue\":\"1100\",\"skipSteps\":3,\"waveForm\":\"sine\",\"timeLag\":100,\"value\":800},\"Relative_Humidity\":{\"allowedValues\":\"0,\",\"minValue\":\"0\",\"maxValue\":\"100\",\"skipSteps\":3,\"waveForm\":\"sine\",\"timeLag\":100,\"value\":80}}";
		String deviceName = "nodes/WeatherSimulator_CN/test";
		JSONObject dataPointJsonObject = (JSONObject) JSONValue.parse(parseDataPoint);
		JSONObject jsonkk = (JSONObject) JSONValue.parse(parseResponse);
	Object object[] = dataPointJsonObject.keySet().toArray();
	public String simulateResponse(String commandName, String commandParameters) {
		JSONArray jsonArr = (JSONArray) jsonkk.get(commandName);
		if(jsonArr==null || jsonArr.size()==0)
		{  
			return "RESPONSE RECEIVED FOR "+commandName.toUpperCase();
		}
		JSONObject mlk = (JSONObject) jsonArr.get(0);
	 	
		JSONObject jso =  (JSONObject)JSONValue.parse(commandParameters);
		if (jso != null) {
		JSONObject fixedResp = (JSONObject) jso.get("fixedResponse");
		if(fixedResp!=null)
		{ 
		Set<String> map =  fixedResp.keySet();
		Iterator<String> iterat = map.iterator();
		String hh = fixedResp.get("Response")+":-";
		while(iterat.hasNext())
		{
			String mm = (String) iterat.next();
			if(!mm.equals("Response"))
			{
			hh= hh+ mm+":"+fixedResp.get(mm)+"||";
			}
		}
		System.out.println(hh);
		return hh;
		}
		} 
		String respName = mlk.keySet().toArray()[0].toString();
		JSONArray respCases = (JSONArray) mlk.get(respName);
		System.out.println(respCases);
		String resp = respName+": ";
		for (int i = 0; i < respCases.size(); i++) {
			String parName = (String) ((JSONObject) respCases.get(i))
					.get("parameterName");
			String value = (String) ((JSONObject) respCases.get(i))
					.get("value");
			String min = (String) ((JSONObject) respCases.get(i))
					.get("minValue");
			String max = (String) ((JSONObject) respCases.get(i))
					.get("maxValue");
			String allowed = (String) ((JSONObject) respCases.get(i))
					.get("allowedValues");
			int parVal = Integer.parseInt(value);
			int minVal = Integer.parseInt(min);
			int maxVal = Integer.parseInt(max);
			ArrayList<Integer> allowedVal = convertToIntArrayList(allowed
					.split(","));

			// System.out.println(min +"  " +max + "  " + value + " " +
			// allowedVal );
			// System.out.println(i);
			int paraVarValue = chooseValueForResponseParameter(parVal, minVal,
					maxVal, allowedVal);
			// System.out.println(parName+":-"+paraVarValue);
			resp = resp + parName + ":-" + paraVarValue + "\t";
		}

		System.out.println(resp);
		return resp;
	}

	private int chooseValueForResponseParameter(int parVal, int minVal,
			int maxVal, ArrayList<Integer> allowedVal) {
		// TODO Auto-generated method stub
		Set<Integer> intSet = new HashSet<Integer>();
		intSet.add(parVal);
		intSet.add(minVal);
		intSet.add(maxVal);
		intSet.addAll(allowedVal);
 
		int size = intSet.size();
		int item = new Random().nextInt(size); // In real life, the Random
												// object should be rather more
												// shared than this
		
		Random rand = new Random(System.currentTimeMillis());
		Object[] setArray = intSet.toArray();
		int _size = intSet.size();
		int _nextInt = rand.nextInt(_size);
		Object _get = setArray[_nextInt];
		int choosenValue = (((Integer) _get)).intValue();
		return choosenValue;
	}

	private ArrayList<Integer> convertToIntArrayList(String[] split) {
		// TODO Auto-generated method stub
		ArrayList<Integer> intArr = new ArrayList<Integer>();
		for (int j = 0; j < split.length; j++) {
			if (split[j] != "") {
				intArr.add(Integer.parseInt(split[j]));
			}  
		}
		return intArr;
	} 

	public void pumpData() {

		for (int j = 0; j < object.length; j++) {
			JSONObject dataPointSimulated = (JSONObject) dataPointJsonObject.get(object[j]);
			final String dataPointName = object[j].toString();
			final String waveForm = dataPointSimulated.get("waveForm").toString();
			final int minValue = Integer.parseInt(dataPointSimulated.get("minValue").toString());
			final int maxValue = Integer.parseInt(dataPointSimulated.get("maxValue").toString());
			final int value = Integer.parseInt(dataPointSimulated.get("value").toString());
			final int timeLag = Integer.parseInt(dataPointSimulated.get("timeLag").toString());
			final int skipSteps = Integer.parseInt(dataPointSimulated.get("skipSteps").toString());
			final int amplitute = Math.abs(maxValue) - Math.abs(minValue);
			new Thread(new Runnable() {
				@Override
				public void run() {
					int i = 0;
					// Do the processing.
					float someNumber = 0.0F;
					try {
						DeviceProxy dp = new DeviceProxy(deviceName);
	 					DeviceAttribute da = new DeviceAttribute(dataPointName);
						while (true) {
							System.out.println("max" + maxValue + "min " + minValue);
							System.out.println("Amplitutde :" + amplitute);
							System.out.println(waveForm);
							if (waveForm.equals("sine")) {
								System.out.println("SINE");
					 			someNumber = (float) ((float)amplitute* Math.sin(2*Math.PI/i)+minValue);
							} else if (waveForm.equals("cosine")) {
			 					someNumber = (float) ((float) amplitute*Math.cos(2*Math.PI/i)+minValue);
			 					System.out.println("COSINE");
							} 
						 	  
							
							da.insert(someNumber);
							System.out.println(someNumber);
							System.out.println("Time Lag"+timeLag);
							dp.write_attribute(da);
							i = i + skipSteps;
							Thread.sleep(timeLag);
						}
					} catch (DevFailed | InterruptedException e) {
						// TODO Auto-generated catch block
						e.printStackTrace();
					}
				}
			}).start();
		}
	}
}