import asyncio
import aiohttp
import random
import logging
from datetime import datetime
import argparse
import time
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("elevator_simulation.log")
    ]
)
logger = logging.getLogger("ElevatorSim")

# Simulation parameters
MAX_FLOOR = 20
BASE_URL = "http://localhost:8002"  # FastAPI service URL
DEFAULT_DURATION = 300  # 5 minutes
DEFAULT_NUM_USERS = 10
DEFAULT_REQUEST_INTERVAL = (5, 20)  # seconds between requests (min, max)

class ElevatorUser:
    """Simulates a person using the elevator system."""
    
    def __init__(self, user_id, session):
        self.user_id = user_id
        self.session = session
        self.current_floor = random.randint(1, MAX_FLOOR)
        self.inside_elevator = False
        logger.info(f"User {user_id} created at floor {self.current_floor}")
    
    async def call_elevator(self):
        """Call the elevator from outside."""
        target_floor = random.randint(1, MAX_FLOOR)
        
        # Don't go to the same floor
        while target_floor == self.current_floor:
            target_floor = random.randint(1, MAX_FLOOR)
        
        # Determine direction
        direction = "up" if target_floor > self.current_floor else "down"
        
        logger.info(f"User {self.user_id} at floor {self.current_floor} calling elevator to go {direction}")
        
        try:
            # Call elevator from outside
            url = f"{BASE_URL}/{self.current_floor}/{direction}"
            async with self.session.post(url) as response:
                if response.status == 200:
                    logger.info(f"User {self.user_id} successfully called elevator at floor {self.current_floor}")
                    return True
                else:
                    response_text = await response.text()
                    logger.error(f"Failed to call elevator: {response.status} - {response_text}")
                    return False
                
        except Exception as e:
            logger.error(f"Error calling elevator: {str(e)}")
            return False
    
    async def wait_for_elevator(self):
        """Wait for the elevator to arrive at the current floor."""
        max_wait_time = 60  # Maximum wait time in seconds
        wait_start = time.time()
        
        logger.info(f"User {self.user_id} waiting for elevator at floor {self.current_floor}")
        
        while time.time() - wait_start < max_wait_time:
            try:
                # Check elevator position
                async with self.session.get(f"{BASE_URL}/floor") as response:
                    if response.status == 200:
                        data = await response.json()
                        elevator_floor = data.get("current_floor")
                        
                        # Also check state to see if elevator is moving or idle
                        async with self.session.get(f"{BASE_URL}/state") as state_response:
                            if state_response.status == 200:
                                state_data = await state_response.json()
                                elevator_state = state_data.get("state")
                                
                                logger.debug(f"Elevator at floor {elevator_floor}, state: {elevator_state}")
                                
                                # If elevator is at our floor and idle or just arrived, enter it
                                if elevator_floor == self.current_floor and (elevator_state == "idle" or 
                                                                            time.time() - wait_start > 5):  # Give it time to stop
                                    logger.info(f"User {self.user_id} entering elevator at floor {self.current_floor}")
                                    self.inside_elevator = True
                                    return True
                    
            except Exception as e:
                logger.error(f"Error checking elevator position: {str(e)}")
            
            # Wait before checking again
            await asyncio.sleep(2)
        
        logger.warning(f"User {self.user_id} gave up waiting after {max_wait_time} seconds")
        return False
    
    async def request_floor(self):
        """Request a floor from inside the elevator."""
        target_floor = random.randint(1, MAX_FLOOR)
        
        # Don't request current floor
        while target_floor == self.current_floor:
            target_floor = random.randint(1, MAX_FLOOR)
        
        logger.info(f"User {self.user_id} inside elevator requesting floor {target_floor}")
        
        try:
            # Request floor from inside
            url = f"{BASE_URL}/go/{target_floor}"
            async with self.session.post(url) as response:
                if response.status == 200:
                    logger.info(f"User {self.user_id} successfully requested floor {target_floor}")
                    return target_floor
                else:
                    response_text = await response.text()
                    logger.error(f"Failed to request floor: {response.status} - {response_text}")
                    return None
                
        except Exception as e:
            logger.error(f"Error requesting floor: {str(e)}")
            return None
    
    async def ride_to_floor(self, target_floor):
        """Ride the elevator to the requested floor."""
        max_ride_time = 60  # Maximum ride time in seconds
        ride_start = time.time()
        
        logger.info(f"User {self.user_id} riding elevator to floor {target_floor}")
        
        while time.time() - ride_start < max_ride_time:
            try:
                # Check elevator position
                async with self.session.get(f"{BASE_URL}/floor") as response:
                    if response.status == 200:
                        data = await response.json()
                        elevator_floor = data.get("current_floor")
                        
                        # Also check state
                        async with self.session.get(f"{BASE_URL}/state") as state_response:
                            if state_response.status == 200:
                                state_data = await state_response.json()
                                elevator_state = state_data.get("state")
                                
                                # If elevator reached our floor, exit
                                if elevator_floor == target_floor and (elevator_state == "idle" or 
                                                                     time.time() - ride_start > 5):  # Give it time to stop
                                    logger.info(f"User {self.user_id} exiting elevator at floor {target_floor}")
                                    self.current_floor = target_floor
                                    self.inside_elevator = False
                                    return True
                    
            except Exception as e:
                logger.error(f"Error checking elevator position: {str(e)}")
            
            # Wait before checking again
            await asyncio.sleep(2)
        
        logger.warning(f"User {self.user_id} ride timed out after {max_ride_time} seconds")
        # Assume we got to the floor anyway to continue simulation
        self.current_floor = target_floor
        self.inside_elevator = False
        return False
    
    async def simulate_usage(self):
        """Complete elevator usage cycle."""
        # Call the elevator
        if await self.call_elevator():
            # Wait for it to arrive
            if await self.wait_for_elevator():
                # Request a floor
                target_floor = await self.request_floor()
                if target_floor:
                    # Ride to the requested floor
                    await self.ride_to_floor(target_floor)

async def check_service_status():
    """Check if the elevator service is running."""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{BASE_URL}/simulation/status") as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get("running", False)
    except Exception:
        return False
    return False

async def ensure_service_running():
    """Make sure the elevator simulation is running."""
    is_running = await check_service_status()
    
    if not is_running:
        logger.info("Starting elevator service simulation...")
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(f"{BASE_URL}/simulation/start") as response:
                    if response.status == 200:
                        logger.info("Elevator service simulation started successfully")
                    else:
                        response_text = await response.text()
                        logger.warning(f"Failed to start elevator service: {response.status} - {response_text}")
        except Exception as e:
            logger.error(f"Error starting elevator service: {str(e)}")
            logger.error("Make sure the elevator service is running on the specified URL")
            return False
    
    return True

async def simulate_user(user_id, duration, request_interval):
    """Simulate a user making multiple elevator requests over time."""
    async with aiohttp.ClientSession() as session:
        user = ElevatorUser(user_id, session)
        
        end_time = time.time() + duration
        
        while time.time() < end_time:
            # Complete one full usage cycle
            await user.simulate_usage()
            
            # Random wait before next request
            wait_time = random.uniform(request_interval[0], request_interval[1])
            logger.info(f"User {user_id} waiting {wait_time:.1f} seconds before next request")
            await asyncio.sleep(wait_time)

async def run_simulation(num_users, duration, request_interval):
    """Run the complete elevator simulation with multiple users."""
    logger.info(f"Starting elevator simulation with {num_users} users for {duration} seconds")
    
    # Make sure the elevator service is running
    if not await ensure_service_running():
        logger.error("Cannot start simulation without elevator service running")
        return
    
    # Create user tasks
    user_tasks = []
    for i in range(1, num_users + 1):
        user_tasks.append(simulate_user(i, duration, request_interval))
    
    # Run all users concurrently
    await asyncio.gather(*user_tasks)
    
    logger.info("Elevator simulation completed")

def main():

    """Parse arguments and start simulation."""
    global BASE_URL

    parser = argparse.ArgumentParser(description='Elevator System Simulation')
    parser.add_argument('--users', type=int, default=DEFAULT_NUM_USERS, 
                        help=f'Number of simultaneous users (default: {DEFAULT_NUM_USERS})')
    parser.add_argument('--duration', type=int, default=DEFAULT_DURATION, 
                        help=f'Simulation duration in seconds (default: {DEFAULT_DURATION})')
    parser.add_argument('--min-interval', type=int, default=DEFAULT_REQUEST_INTERVAL[0], 
                        help=f'Minimum seconds between user requests (default: {DEFAULT_REQUEST_INTERVAL[0]})')
    parser.add_argument('--max-interval', type=int, default=DEFAULT_REQUEST_INTERVAL[1], 
                        help=f'Maximum seconds between user requests (default: {DEFAULT_REQUEST_INTERVAL[1]})')
    parser.add_argument('--url', type=str, default=BASE_URL, 
                        help=f'Elevator service URL (default: {BASE_URL})')
    parser.add_argument('--verbose', action='store_true', 
                        help='Enable debug logging')
    
    args = parser.parse_args()
    
    # Set logging level
    if args.verbose:
        logger.setLevel(logging.DEBUG)
    
    # Update global settings
    BASE_URL = args.url
    
    # Configure request interval
    request_interval = (args.min_interval, args.max_interval)
    
    try:
        # Run the simulation
        asyncio.run(run_simulation(args.users, args.duration, request_interval))
    except KeyboardInterrupt:
        logger.info("Simulation interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Simulation error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()