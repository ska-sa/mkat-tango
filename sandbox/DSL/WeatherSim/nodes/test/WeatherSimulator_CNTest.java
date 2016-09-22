package com.tango.nodes.test;
		  
import org.testng.Assert;

import org.testng.annotations.Test;
import org.testng.annotations.DataProvider;
  
import fr.esrf.Tango.DevFailed;
import fr.esrf.TangoApi.DeviceData;
import fr.esrf.TangoApi.DeviceProxy;
 
public class WeatherSimulator_CNTest
{ 

@Test(dataProvider="on") 
		public void ON(String params) throws DevFailed {
		DeviceProxy dp =new  DeviceProxy("nodes/WeatherSimulator_CN/test");
			 			DeviceData dd = new fr.esrf.TangoApi.DeviceData();
	dd.insert(params);
	String resp = dp.command_inout("ON",dd).extractString();
	System.out.println(resp);
	Assert.assertEquals(resp,"RES_ON:-msg:0||");
	}  
	
@DataProvider(name="on")
	public Object[][] onDataProvider() {
	return new Object[][]{
	
			
			new Object[] {"{\"fixedResponse\":{\"Response\":\"RES_ON\",\"msg\":0},\"ON\":[]}"},
			
			new Object[] {"{\"ON\":[]}"},
			
			new Object[] {"{\"ON\":[]}"},
			
			new Object[] {"{\"ON\":[]}"},
			
			new Object[] {"{\"fixedResponse\":{\"Response\":\"RES_ON\",\"msg\":0},\"ON\":[]}"},
	 
	
				 		};
}  

@Test(dataProvider="off") 
		public void OFF(String params) throws DevFailed {
		DeviceProxy dp =new  DeviceProxy("nodes/WeatherSimulator_CN/test");
			 			DeviceData dd = new fr.esrf.TangoApi.DeviceData();
	dd.insert(params);
	String resp = dp.command_inout("OFF",dd).extractString();
	System.out.println(resp);
	Assert.assertEquals(resp,"RES_OFF:-msg:0||");
	}  
	
@DataProvider(name="off")
	public Object[][] offDataProvider() {
	return new Object[][]{
	
			
			new Object[] {"{\"OFF\":[]}"},
			
			new Object[] {"{\"OFF\":[]}"},
			
			new Object[] {"{\"OFF\":[],\"fixedResponse\":{\"Response\":\"RES_OFF\",\"msg\":0}}"},
			
			new Object[] {"{\"OFF\":[],\"fixedResponse\":{\"Response\":\"RES_OFF\",\"msg\":0}}"},
			
			new Object[] {"{\"OFF\":[],\"fixedResponse\":{\"Response\":\"RES_OFF\",\"msg\":0}}"},
	 
	
				 		};
}  

@Test(dataProvider="reset") 
		public void RESET(String params) throws DevFailed {
		DeviceProxy dp =new  DeviceProxy("nodes/WeatherSimulator_CN/test");
			 			DeviceData dd = new fr.esrf.TangoApi.DeviceData();
	dd.insert(params);
	String resp = dp.command_inout("RESET",dd).extractString();
	System.out.println(resp);
	Assert.assertEquals(resp,"RES_RESET:-msg:0||");
	}  
	
@DataProvider(name="reset")
	public Object[][] resetDataProvider() {
	return new Object[][]{
	
			
			new Object[] {"{\"RESET\":[]}"},
			
			new Object[] {"{\"RESET\":[]}"},
			
			new Object[] {"{\"RESET\":[],\"fixedResponse\":{\"Response\":\"RES_RESET\",\"msg\":0}}"},
			
			new Object[] {"{\"RESET\":[]}"},
			
			new Object[] {"{\"RESET\":[]}"},
	 
	
				 		};
}  
}