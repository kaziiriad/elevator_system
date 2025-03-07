import asyncio
from fastapi import BackgroundTasks, FastAPI, HTTPException
import logging
from service import get_current_floor, get_current_state, call, go_to
from contextlib import asynccontextmanager

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    handlers=[
        logging.StreamHandler(),  # Log to console
        logging.FileHandler("elevator_system.log")  # Also log to a file
    ]
                    
)
logger = logging.getLogger(__name__)

service_logger = logging.getLogger("service")
service_logger.setLevel(logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup code
    logger.info("Elevator service is starting up")
    background_tasks = BackgroundTasks()
    await start_simulation(background_tasks)
    
    yield  # This is where the app runs
    
    # Shutdown code
    logger.info("Elevator service is shutting down")
    global simulation_running
    simulation_running = False

app = FastAPI(title="Elevator Control System", 
              description="API for controlling an elevator system",
              lifespan=lifespan
              )

simulation_running = False
MAX_FLOOR = 20  # Define a constant

# In main.py, update the simulation loop for faster checks:
async def run_elevator_simulation():
    global simulation_running
    logger.info("Starting elevator simulation background task")
    simulation_running = True
    try:
        while simulation_running:  # Exit loop when flag is False
            await go_to()
            await asyncio.sleep(0.5)  # Reduced sleep time
    except Exception as e:
        logger.error(f"Error in elevator simulation loop: {str(e)}")
    finally:
        simulation_running = False
        

# from the outside of the elevator
@app.get("/")
def read_root():
    return {"message": "Welcome to the elevator service."}

@app.get("/state")
async def get_state():
    """Get the current state of the elevator."""
    try:
        state = await get_current_state()
        return state
    except Exception as e:
        logger.error(f"Error getting elevator state: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get elevator state: {str(e)}")

@app.get("/floor")
async def current_floor():
    """Get the current floor of the elevator."""
    try:
        floor = await get_current_floor()
        return {"current_floor": floor}
    except Exception as e:
        logger.error(f"Error getting current floor: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get current floor: {str(e)}")


# from the inside of the elevator
@app.post("/go/{floor}")
async def go_to_floor(floor: int):
    """Request the elevator to go to a specific floor (from inside)."""
    try:
        if floor > MAX_FLOOR or floor < 1:
            raise HTTPException(status_code=400, detail=f"Floor must be between 1 and {MAX_FLOOR}")

        if not isinstance(floor, int) or floor < 1:
            raise HTTPException(status_code=400, detail="Floor must be a positive integer")
        
        await call(floor=floor)
        return {
            "message": "Request submitted successfully",
            "destination_floor": floor
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing go_to request: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to process request: {str(e)}")

#from the outside of the elevator
@app.post("/{floor}/up")
async def go_up(floor: int):
    """Call the elevator to go up from a specific floor (from outside)."""
    try:
        if not isinstance(floor, int) or floor < 1:
            raise HTTPException(status_code=400, detail="Floor must be a positive integer")
        
        await call(floor, "up")
        return {
            "message": "Request submitted successfully",
            "called_from_floor": floor,
            "direction": "up"
        }
    except Exception as e:
        logger.error(f"Error processing up call request: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to process request: {str(e)}")

@app.post("/{floor}/down")
async def go_down(floor: int):
    """Call the elevator to go down from a specific floor (from outside)."""
    try:
        if not isinstance(floor, int) or floor < 1:
            raise HTTPException(status_code=400, detail="Floor must be a positive integer")
        
        await call(floor, "down")
        return {
            "message": "Request submitted successfully",
            "called_from_floor": floor,
            "direction": "down"
        }
    except Exception as e:
        logger.error(f"Error processing down call request: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to process request: {str(e)}")
@app.post("/simulation/start")
async def start_simulation(background_tasks: BackgroundTasks):
    """Start the elevator simulation."""
    global simulation_running
    
    if simulation_running:
        return {"message": "Simulation is already running"}
    
    background_tasks.add_task(run_elevator_simulation)
    return {"message": "Elevator simulation started"}

@app.post("/simulation/stop")
async def stop_simulation():
    """Stop the elevator simulation."""
    global simulation_running
    
    if not simulation_running:
        return {"message": "Simulation is not running"}
    
    simulation_running = False
    return {"message": "Elevator simulation stopping..."}

@app.get("/simulation/status")
async def simulation_status():
    """Get the status of the elevator simulation."""
    global simulation_running
    return {"running": simulation_running}

if __name__ == "__main__":
    import uvicorn
    logger.info("Starting elevator service...")

    uvicorn.run("main:app", host="0.0.0.0", port=8002, reload=True)