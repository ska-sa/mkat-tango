

/*----- PROTECTED REGION END -----*///	WeatherSimulator_CN.java


package com.tango.nodes.java;

import com.tango.nodes.simulators.WeatherSimulator_CNSimulator;

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

/*----- PROTECTED REGION END -----*///	WeatherSimulator_CN.imports
  
@Device
public class WeatherSimulator_CN {

	public static final Logger logger = LoggerFactory.getLogger(WeatherSimulator_CN.class);
	private static final XLogger xlogger = XLoggerFactory
			.getXLogger(WeatherSimulator_CN.class);
	// private static String instance;
	// ========================================================
	// Programmer's data members
	// ========================================================
	/*----- PROTECTED REGION ID(WeatherSimulator_CN.variables) ENABLED START -----*/

	// Put static variables here

	/*----- PROTECTED REGION END -----*/// WeatherSimulator_CN.variables
	/*----- PROTECTED REGION ID(WeatherSimulator_CN.private) ENABLED START -----*/


	// Put private variables here
	private Map<Integer, Alarm> alarmMap;
	private PipeBlob responsePipeBlob;
    private PipeBlob alarmPipeBlob;
	private static String deviceName = "nodes/WeatherSimulator_CN/test";
	
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
	 	state = DevState.INIT;
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
	@Attribute(name="Temperature")
	@AttributeProperties(minAlarm="-10",maxAlarm="55")
			 		private float Temperature ;
	public synchronized float getTemperature(){
		return this.Temperature;
	}
	public synchronized void setTemperature(float Temperature) throws DevFailed{
		this.Temperature  = Temperature;
	} 
	@Attribute(name="Insolation")
	@AttributeProperties(minAlarm="0",maxAlarm="1200")
			 		private float Insolation ;
	public synchronized float getInsolation(){
		return this.Insolation;
	}
	public synchronized void setInsolation(float Insolation) throws DevFailed{
		this.Insolation  = Insolation;
	} 
	@Attribute(name="Pressure")
	@AttributeProperties(minAlarm="500",maxAlarm="1100")
			 		private float Pressure ;
	public synchronized float getPressure(){
		return this.Pressure;
	}
	public synchronized void setPressure(float Pressure) throws DevFailed{
		this.Pressure  = Pressure;
	} 
	@Attribute(name="Rainfall")
	@AttributeProperties(minAlarm="0",maxAlarm="4")
			 		private float Rainfall ;
	public synchronized float getRainfall(){
		return this.Rainfall;
	}
	public synchronized void setRainfall(float Rainfall) throws DevFailed{
		this.Rainfall  = Rainfall;
	} 
	@Attribute(name="Wind_Speed")
	@AttributeProperties(minAlarm="0",maxAlarm="30")
			 		private float Wind_Speed ;
	public synchronized float getWind_Speed(){
		return this.Wind_Speed;
	}
	public synchronized void setWind_Speed(float Wind_Speed) throws DevFailed{
		this.Wind_Speed  = Wind_Speed;
	} 
	@Attribute(name="Wind_Direction")
	@AttributeProperties(minAlarm="0",maxAlarm="360")
			 		private float Wind_Direction ;
	public synchronized float getWind_Direction(){
		return this.Wind_Direction;
	}
	public synchronized void setWind_Direction(float Wind_Direction) throws DevFailed{
		this.Wind_Direction  = Wind_Direction;
	} 
	@Attribute(name="Relative_Humidity")
	@AttributeProperties(minAlarm="0",maxAlarm="100")
			 		private float Relative_Humidity ;
	public synchronized float getRelative_Humidity(){
		return this.Relative_Humidity;
	}
	public synchronized void setRelative_Humidity(float Relative_Humidity) throws DevFailed{
		this.Relative_Humidity  = Relative_Humidity;
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
	@Command(name="ON" 
	 )
	 public String ON(String ONParams) throws DevFailed {
	xlogger.entry();
			String ONOut;
			/*----- PROTECTED REGION ID(WeatherSimulator_CN.ON) ENABLED START -----*/
	        //	Put command code here
			state = DevState.ON;
			xlogger.exit();
			ONOut = new WeatherSimulator_CNSimulator().simulateResponse("ON",ONParams);
			return ONOut;
		} 
	@Command(name="OFF" 
	 )
	 public String OFF(String OFFParams) throws DevFailed {
	xlogger.entry();
			String OFFOut;
			/*----- PROTECTED REGION ID(WeatherSimulator_CN.OFF) ENABLED START -----*/
	        //	Put command code here
			state = DevState.OFF;
			xlogger.exit();
			OFFOut = new WeatherSimulator_CNSimulator().simulateResponse("OFF",OFFParams);
			return OFFOut;
		} 
	@Command(name="RESET" 
	 )
	 public String RESET(String RESETParams) throws DevFailed {
	xlogger.entry();
			String RESETOut;
			/*----- PROTECTED REGION ID(WeatherSimulator_CN.RESET) ENABLED START -----*/
	        //	Put command code here
			state = DevState.STANDBY;
			xlogger.exit();
			RESETOut = new WeatherSimulator_CNSimulator().simulateResponse("RESET",RESETParams);
			return RESETOut;
		} 
	


	
	/*----- PROTECTED REGION END -----*/// WeatherSimulator_CN.methods

	/**
	 * Starts the server.
	 * 
	 * @param args
	 *            program arguments (instance_name [-v[trace level]] [-nodb
	 *            [-dlist <device name list>] [-file=fileName]])
	 */
	public static void main(final String[] args) {
		//DataBaseHandler.addDevice(deviceName); // Uncomment this to enter the device into the database
		ServerManager.getInstance().start(args, WeatherSimulator_CN.class);
		new WeatherSimulator_CNSimulator().pumpData();
		logger.info("------- Started -------------");

	}

}
