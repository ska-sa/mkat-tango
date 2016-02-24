

/*----- PROTECTED REGION END -----*///	SIMPLE_CN.java


package com.tango.nodes.java;

import com.tango.nodes.simulators.SIMPLE_CNSimulator;

/*----- PROTECTED REGION ENABLED START -----*/

import com.tango.nodes.utils.*;
import fr.esrf.Tango.DevFailed;
import fr.esrf.Tango.DevState;
import fr.esrf.Tango.DispLevel;
import fr.esrf.TangoApi.DevicePipe;
import fr.esrf.TangoApi.PipeBlob;
import fr.esrf.TangoApi.PipeDataElement;
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
import org.tango.server.pipe.PipeValue;

import java.util.HashMap;
import java.util.Map;
import java.util.Random;

import static java.lang.Thread.sleep;


//	Import Tango IDL types
// additional imported packages

/*----- PROTECTED REGION END -----*///	SIMPLE_CN.imports
  
@Device
public class SIMPLE_CN {

	public static final Logger logger = LoggerFactory.getLogger(SIMPLE_CN.class);
	private static final XLogger xlogger = XLoggerFactory
			.getXLogger(SIMPLE_CN.class);
	// private static String instance;
	// ========================================================
	// Programmer's data members
	// ========================================================
	/*----- PROTECTED REGION ID(SIMPLE_CN.variables) ENABLED START -----*/

	// Put static variables here

	/*----- PROTECTED REGION END -----*/// SIMPLE_CN.variables
	/*----- PROTECTED REGION ID(SIMPLE_CN.private) ENABLED START -----*/


	// Put private variables here
	private Map<Integer, Alarm> alarmMap;
	private PipeBlob responsePipeBlob;
    private PipeBlob alarmPipeBlob;
	private static String deviceName = "nodes/SIMPLE_CN/test";
	
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
	@Attribute(name="Temp")
			 		private float temp ;
	public synchronized float gettemp(){
		return this.temp;
	}
	public synchronized void settemp(float temp) throws DevFailed{
		this.temp  = temp;
	} 
	@Attribute(name="Wind_speed")
			 		private float wind_speed ;
	public synchronized float getwind_speed(){
		return this.wind_speed;
	}
	public synchronized void setwind_speed(float wind_speed) throws DevFailed{
		this.wind_speed  = wind_speed;
	} 

	
	//========================================================
	//	Pipe data members and related methods
	//========================================================
	/**
	 * Pipe Response
	 * description:
	 *     
	 */
	@Pipe(description="", displayLevel=DispLevel._OPERATOR, label="Response")
	private PipeValue response;
	/**
	 * Read Pipe Response
	 * 
	 * @return attribute value
	 * @throws DevFailed if read pipe failed.
	 */
	public PipeValue getResponse() throws DevFailed {
		xlogger.entry();
		/*----- PROTECTED REGION ID(LeafNode.getResponse) ENABLED START -----*/

        //	Put read attribute code here
		
		/*----- PROTECTED REGION END -----*/	//	LeafNode.getResponse
		xlogger.exit();
		return response;
	}
	/**
	 * Pipe Alarm
	 * description:
	 *     
	 */
	@Pipe(description="", displayLevel=DispLevel._OPERATOR, label="Alarm")
	private PipeValue alarm;
	/**
	 * Read Pipe Alarm
	 * 
	 * @return attribute value
	 * @throws DevFailed if read pipe failed.
	 */
	public PipeValue getAlarm() throws DevFailed {
		xlogger.entry();
		/*----- PROTECTED REGION ID(LeafNode.getAlarm) ENABLED START -----*/
        //	Put read attribute code here
		
		/*----- PROTECTED REGION END -----*/	//	LeafNode.getAlarm
		xlogger.exit();
		return alarm;
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
	@Command(name="CONNECT" 
	 )
	 public String CONNECT(String CONNECTParams) throws DevFailed {
	xlogger.entry();
			String CONNECTOut;
			/*----- PROTECTED REGION ID(SIMPLE_CN.CONNECT) ENABLED START -----*/
	        //	Put command code here
			xlogger.exit();
			CONNECTOut = new SIMPLE_CNSimulator().simulateResponse("CONNECT",CONNECTParams);
			return CONNECTOut;
		} 
	


	
	/*----- PROTECTED REGION END -----*/// SIMPLE_CN.methods

	/**
	 * Starts the server.
	 * 
	 * @param args
	 *            program arguments (instance_name [-v[trace level]] [-nodb
	 *            [-dlist <device name list>] [-file=fileName]])
	 */
	public static void main(final String[] args) {
		//DataBaseHandler.addDevice(deviceName); // Uncomment this to enter the device into the database
		ServerManager.getInstance().start(args, SIMPLE_CN.class);
		logger.info("------- Started -------------");

	}

}

