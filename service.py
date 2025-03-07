import asyncio
import aioredis
import logging

logger = logging.getLogger(__name__)
# Connect to Redis 
once = 0

redis_client = aioredis.from_url('redis://localhost:6379')

# get current state
# async def get_current_state():
#     state = await redis_client.hgetall('state')
#     if not state:
#         state = {
#             "floor" : 1,
#             "state": "idle"
#         }
#         await set_current_state(state)
#         return state
#     return {key.decode(): value.decode() for key, value in state.items()}
async def get_current_state():
    try:
        # Check if the key exists and what type it is
        key_type = await redis_client.type('state')
        
        # If the key exists but is not a hash, delete it
        if key_type and key_type != b'hash':
            logging.warning(f"'state' key exists but is of type {key_type.decode()}, deleting it")
            await redis_client.delete('state')
            
        state = await redis_client.hgetall('state')
        if not state:
            state = {
                "floor": 1,
                "state": "idle"
            }
            await set_current_state(state)
            return state
        return {key.decode(): value.decode() for key, value in state.items()}
    except Exception as e:
        import traceback
        error_location = traceback.extract_tb(e.__traceback__)[-1]
        file_name = error_location.filename.split('/')[-1]
        line_number = error_location.lineno
        logging.error(f"Error in get_current_state at {file_name}:{line_number}: {e}")
        logging.debug(f"Full traceback: {traceback.format_exc()}")
        # Return default state in case of error
        return {"floor": 1, "state": "idle"}
    
# set the current state
async def set_current_state(state):
    await redis_client.hmset('state', state)

# Get the current floor
async def get_current_floor():
    current_floor = await redis_client.get('current_floor')
    return int(current_floor) if current_floor else 1

# Set the current floor
async def set_current_floor(floor):
    await redis_client.set('current_floor', floor)

async def add_floor(direction, floor):
    await redis_client.zadd(direction, {f'floor_{floor}': floor})

# Inside the elevator operation

async def get_next_floor(direction, current_floor):
    if direction == 'up':
        next_floors = await redis_client.zrangebyscore(
            direction, current_floor, float('inf'), start=0, num=1, withscores=True
        )
    elif direction == 'down':
        next_floors = await redis_client.zrevrangebyscore(
            direction, current_floor, 0, start=0, num=1, withscores=True
        )
    else:
        return None

    if next_floors:
        next_floor = next_floors[0][0].decode()
        await redis_client.zrem(direction, next_floor)
        return next_floor
    return None


# async def set_go_to(floor, direction=""):

    
#     current_floor = await get_current_floor()
#     if direction:
#         await redis_client.rpush(direction, floor)
#     if current_floor == floor:
#         return "Already at the desired floor"
#     elif current_floor < floor:
#         await redis_client.lpush("up", floor)
#     else:
#         await redis_client.lpush("down", floor)

# call from outside
async def call(floor, direction=None):
    global once
    once = 0
    try:
        current_floor = await get_current_floor()

        if direction: # from outside the elevator
            logger.info(f"External call from floor {floor} from floor {current_floor}, direction {direction}")
            
            if floor > current_floor:
                pickup_queue = "up"
            elif floor < current_floor:
                pickup_queue = "down"
            else:
                logger.info("Already at floor")
            # Add to pickup queue (up/down)
            await add_floor(pickup_queue, floor)
            
            # Store intended direction for post-pickup (e.g., "up")
            await redis_client.hset(f"floor_{floor}", "intended_direction", direction)

        else: # when the call is from inside the elevator
            logger.info(f"Internal call to floor {floor} from floor {current_floor}")

            if current_floor == floor:
                logger.info(f"Already at the requested floor {floor}")
                return "Already at the requested floor"
            elif current_floor < floor:
                await add_floor("up", floor)
            else:
                await add_floor("down", floor)
        # Log the current state of the queues for debugging
        up_queue = await redis_client.zrange("up", 0, -1, withscores=True)
        down_queue = await redis_client.zrange("down", 0, -1, withscores=True)
        logger.debug(f"Current up queue: {up_queue}")
        logger.debug(f"Current down queue: {down_queue}")
    except Exception as e:
        import traceback
        error_location = traceback.extract_tb(e.__traceback__)[-1]
        file_name = error_location.filename.split('/')[-1]
        line_number = error_location.lineno
        logger.error(f"Error in call function at {file_name}:{line_number}: {e}")
        logger.debug(f"Full traceback: {traceback.format_exc()}")
        raise e

    # Get the list of floors to go to
# async def get_sorted_queue(direction, descending=False):
#     queue_items = await redis_client.lrange(direction, 0, -1)
#     sorted_queue = sorted([int(floor) for floor in queue_items], reverse=descending)
#     # For "up", sort ascending (1, 2, 3)
#     if direction == "up":
#         sorted_queue = sorted(sorted_queue, reverse=descending)
#     # For "down", sort descending (5, 4, 3)
#     elif direction == "down":
#         sorted_queue = sorted(sorted_queue, reverse=descending)
#     return sorted_queue

# Get all queues (both up and down) as sorted lists

#simulate go to floor...
async def go_to():
    global once
    try:

        current_state = await get_current_state()
        current_floor = int(current_state["floor"])
        current_direction = current_state["state"]

        next_floor = None
        new_direction = current_direction

        if current_direction == "up":
            next_floor = await get_next_floor("up", current_floor)
            if not next_floor:
                next_floor = await get_next_floor("down", current_floor)
                new_direction = "down" if next_floor else "idle" #
        elif current_direction == "down":
            next_floor = await get_next_floor("down", current_floor)
            if not next_floor:
                next_floor = await get_next_floor("up", current_floor)
                new_direction = "up" if next_floor else "idle" #

        else:
            next_floor_up = await get_next_floor("up", current_floor)
            next_floor_down = await get_next_floor("down", current_floor)

            if next_floor_up and next_floor_down:
                # Choose the nearest floor
                floor_up = int(next_floor_up.split("_")[1])
                floor_down = int(next_floor_down.split("_")[1])
                if abs(current_floor - floor_up) <= abs(current_floor - floor_down):
                    next_floor = next_floor_up
                    new_direction = "up"
                else:
                    next_floor = next_floor_down
                    new_direction = "down"
            elif next_floor_up:
                next_floor = next_floor_up
                new_direction = "up"
            elif next_floor_down:
                next_floor = next_floor_down
                new_direction = "down"
            else:
                next_floor = None
                new_direction = "idle"

        
        if next_floor:
            floor_number = int(next_floor.split("_")[1])


            if new_direction == "down":
                for fl in range(current_floor, floor_number-1, -1):
                    
                    await set_current_floor(fl)
                    await set_current_state({"floor": fl, "state": new_direction})

                    logger.info(f"Moving {new_direction}")
                    logger.info(f"Current Floor: {fl}")
                    await asyncio.sleep(1) # simulate elevator movement time
            elif new_direction == "up":
                for fl in range(current_floor, floor_number+1):
                    await set_current_floor(fl)
                    await set_current_state({"floor": fl, "state": new_direction})

                    logger.info(f"Moving {new_direction}")
                    logger.info(f"Current Floor: {fl}")
                    await asyncio.sleep(1) # simulate elevator movement time
                
            await set_current_state({"floor": floor_number, "state": new_direction})
            await set_current_floor(floor_number)
            logger.info(f"Reached {floor_number}")


            intended_direction = await redis_client.hget(f"floor_{floor_number}", "intended_direction")

            if intended_direction:
                logger.info(f"Intended direction for floor {floor_number}: {intended_direction.decode()}")
                await redis_client.hdel(f"floor_{floor_number}", "intended_direction")
                # Set the elevator's direction to the intended direction
                new_direction = intended_direction.decode()
                await set_current_state({"floor": floor_number, "state": new_direction})

            logger.info("Opening door...")
            await asyncio.sleep(2) # simulate door opening time
            logger.info("Closing door...")
            
        else:
            logger.info("No more floors to go to")
            if once != 1:
                logger.info("Stopping elevator...")
                once = 1
                await set_current_state({"floor": current_floor, "state": "idle"})
                logging.info("Stopped elevator")
                logging.info(f"Current State: {current_state['state']}, Current Floor: {current_floor}")
            else:
                logger.info(f"Elevator is at {current_state['state']} state, Current Floor: {current_floor}")
                await asyncio.sleep(2) # simulate stopping elevator time
        
    except Exception as e:
        logger.error(f"Error processing go_to request: {str(e)}")
        raise e