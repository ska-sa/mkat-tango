

/*----- PROTECTED REGION END -----*///	MaxLabPowerSupply_CN.java


package com.tango.nodes.java;

import com.tango.nodes.simulators.MaxLabPowerSupply_CNSimulator;

/*----- PROTECTED REGION ENABLED START -----*/

import com.tango.nodes.utils.*;
import fr.esrf.Tango.DevFailed;
import fr.esrf.Tango.DevState;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.slf4j.ext.XLogger;
import org.slf4j.ext.XLoggerFactory;
import org.tango.DeviceState;
import org.tango.server.InvocationContext;
import org.tango.server.ServerManager;
import org.tango.server.annotation.*;
import org.tango.server.attribute.AttributeValue;
import org.tango.server.device.DeviceManager;
import org.tango.server.dynamic.DynamicManager;
import org.tango.server.events.EventType;

import java.util.HashMap;
import java.util.Map;
import java.util.Random;

import static java.lang.Thread.sleep;


//	Import Tango IDL types
// additional imported packages

/*----- PROTECTED REGION END -----*///	MaxLabPowerSupply_CN.imports
  
@Device
public class MaxLabPowerSupply_CN {

	public static final Logger logger = LoggerFactory.getLogger(MaxLabPowerSupply_CN.class);
	private static final XLogger xlogger = XLoggerFactory
			.getXLogger(MaxLabPowerSupply_CN.class);
	// private static String instance;
	// ========================================================
	// Programmer's data members
	// ========================================================
	/*----- PROTECTED REGION ID(MaxLabPowerSupply_CN.variables) ENABLED START -----*/

	// Put static variables here

	/*----- PROTECTED REGION END -----*/// MaxLabPowerSupply_CN.variables
	/*----- PROTECTED REGION ID(MaxLabPowerSupply_CN.private) ENABLED START -----*/


	// Put private variables here
	private Map<Integer, Alarm> alarmMap;
	private static String deviceName = "nodes/MaxLabPowerSupply_CN/test";
	
	//========================================================
	//	Property data members and related methods
	//========================================================
	
	//========================================================
	//	Miscellaneous methods
	//========================================================
	/**
	 * Initialize the device.
	 * 
	 * @throws DevFailed if something fails during the device initialization.
	 */
	@Init(lazyLoading = false)
	public void initDevice() throws DevFailed {
		xlogger.entry();
	 	logger.debug("init device " + deviceManager.getName());
		/*----- PROTECTED REGION ID(LeafNode.initDevice) ENABLED START -----*/

        //	Put your device initialization code here
	 	//setState(DevState.OFF);
	 	//setStatus(DevState.OFF.toString());
	 	OFF(" ");
        /*----- PROTECTED REGION END -----*/	//	LeafNode.initDevice
		xlogger.exit();
	}
	
	
        //	Put your code here
		
		/*----- PROTECTED REGION END -----*/	//	LeafNode.setDynamicManager

	
	/**
	 * Device management. Will be injected by the framework.
	 */
	@DeviceManagement
	DeviceManager deviceManager;
	public void setDeviceManager(DeviceManager deviceManager){
		this.deviceManager= deviceManager ;
	}
	
	// ========================================================
	// Attribute data members and related methods
	// ========================================================
	@Attribute(name="Current")
	@AttributeProperties(minAlarm="0",maxAlarm="360")
			 		private float current = 10;
	public synchronized float getCurrent(){
		return this.current;
	}
	public synchronized void setCurrent(float current) throws DevFailed{
		this.current  = current;
	} 
	@Attribute(name="Voltage")
	@AttributeProperties(minAlarm="0",maxAlarm="100")
			 		private float voltage = 50;
	public synchronized float getVoltage(){
		return this.voltage;
	}
	public synchronized void setVoltage(float voltage) throws DevFailed{
		this.voltage  = voltage;
	} 
	@Attribute(name="Current_set_point")
	@AttributeProperties(minAlarm="0",maxAlarm="69")
			 		private float current_set_point = 13 ;
	public synchronized float getCurrent_set_point(){
		return this.current_set_point;
	}
	public synchronized void setCurrent_set_point(float current_set_point) throws DevFailed{
		this.current_set_point  = current_set_point;
	} 

	

	
	//========================================================
	//	Command data members and related methods
	//========================================================
	/**
	 * The state of the device
	*/
	@State
	private DevState state = DevState.UNKNOWN;
	/**
	 * Execute command "State".
	 * description: This command gets the device state (stored in its 'state' data member) and returns it to the caller.
	 * @return Device state
	 * @throws DevFailed if command execution failed.
	 */
	public final DevState getState() throws DevFailed {
		/*----- PROTECTED REGION ID(LeafNode.getState) ENABLED START -----*/

        //	Put state code here
		
		/*----- PROTECTED REGION END -----*/	//	LeafNode.getState
		return state;
	}
	/**
	 * Set the device state
	 * @param state the new device state
	 */
	public void setState(final DevState state) {
		this.state = state;
	}
	
	/**
	 * The status of the device
	 */
	@Status
	private String status = "Server is starting. The device state is unknown";
	/**
	 * Execute command "Status".
	 * description: This command gets the device status (stored in its 'status' data member) and returns it to the caller.
	 * @return Device status
	 * @throws DevFailed if command execution failed.
	 */
	public final String getStatus() throws DevFailed {
		/*----- PROTECTED REGION ID(LeafNode.getStatus) ENABLED START -----*/

        //	Put status code here
		
		/*----- PROTECTED REGION END -----*/	//	LeafNode.getStatus
		return status;
	}
	/**
	 * Set the device status
	 * @param status the new device status
	 */
	public void setStatus(final String status) {
		this.status = status;
	}
	@Command(name="ON" 
	 )
	 public String ON(String ONParams) throws DevFailed {
	xlogger.entry();
			String ONOut;
			/*----- PROTECTED REGION ID(MaxLabPowerSupply_CN.ON) ENABLED START -----*/
	        //	Put command code here
			setState(DevState.ON);
		 	setStatus(DevState.ON.toString());
		 	setCurrent(10.0F);
		 	setVoltage(50.0F);
		 	setCurrent_set_point(13.0F);
			xlogger.exit();
			ONOut = new MaxLabPowerSupply_CNSimulator().simulateResponse("ON",ONParams);
			return ONOut;
		} 
	@Command(name="OFF" 
	 )
	 public String OFF(String OFFParams) throws DevFailed {
	xlogger.entry();
			String OFFOut;
			/*----- PROTECTED REGION ID(MaxLabPowerSupply_CN.OFF) ENABLED START -----*/
	        //	Put command code here
			setState(DevState.OFF);
		 	setStatus(DevState.OFF.toString());
		 	setCurrent(0.0F);
		 	setVoltage(0.0F);
		 	setCurrent_set_point(0.0F);
			xlogger.exit();
			OFFOut = new MaxLabPowerSupply_CNSimulator().simulateResponse("OFF",OFFParams);
			return OFFOut;
		} 
	@Command(name="RESET" 
	 )
	 public String RESET(String RESETParams) throws DevFailed {
	xlogger.entry();
			String RESETOut;
			/*----- PROTECTED REGION ID(MaxLabPowerSupply_CN.RESET) ENABLED START -----*/
	        //	Put command code here
			setCurrent(10.0F);
		 	setVoltage(50.0F);
		 	setCurrent_set_point(13.0F);
		 	
			//initDevice();
			
			xlogger.exit();
			RESETOut = new MaxLabPowerSupply_CNSimulator().simulateResponse("RESET",RESETParams);
			return RESETOut;
		} 
	@Command(name="SENDCMD" 
	 )
	 public String SENDCMD(String SENDCMDParams) throws DevFailed {
	xlogger.entry();
			String SENDCMDOut;
			/*----- PROTECTED REGION ID(MaxLabPowerSupply_CN.SENDCMD) ENABLED START -----*/
	        //	Put command code here
			xlogger.exit();
			SENDCMDOut = new MaxLabPowerSupply_CNSimulator().simulateResponse("SENDCMD",SENDCMDParams);
			return SENDCMDOut;
		} 
	


	
	/*----- PROTECTED REGION END -----*/// MaxLabPowerSupply_CN.methods

	/**
	 * Starts the server.
	 * 
	 * @param args
	 *            program arguments (instance_name [-v[trace level]] [-nodb
	 *            [-dlist <device name list>] [-file=fileName]])
	 * @throws DevFailed 
	 */
	public static void main(final String[] args) throws DevFailed {
		DataBaseHandler.addDevice(deviceName); // Uncomment this to enter the device into the database
		ServerManager.getInstance().start(args, MaxLabPowerSupply_CN.class);
		logger.info("------- Started -------------");

	}

}

