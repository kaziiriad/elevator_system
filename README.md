


# Elevator System

A real-time elevator simulation and control system that models elevator behavior in multi-story buildings.

## Overview

This project implements a realistic elevator control system with the following components:

- **Elevator Service**: A FastAPI backend that manages elevator state and processes requests
- **Elevator Simulation**: A Python script that simulates real-world elevator usage patterns
- **Redis**: Used for state management and inter-process communication

The system implements standard elevator algorithms including:
- Directional prioritization (serving floors in the current direction of travel first)
- Intelligent dispatching (selecting the optimal elevator for each request)
- Capacity management

## Features

- Multiple elevators with independent operation
- Support for both internal (from inside elevator) and external (from floors) calls
- Real-time state tracking and visualization
- Configurable simulation parameters
- RESTful API for integration with other systems
- Persistent state using Redis

## Requirements

- Python 3.10+
- Docker and Docker Compose (for Redis)
- Required Python packages (see `pyproject.toml`)

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/kaziiriad/elevator-system.git
   cd elevator-system
   ```

2. Install dependencies:
   ```bash
   pip install -e .
   ```

3. Start the Redis server and elevator service using Docker Compose:
   ```bash
   docker-compose up -d
   ```

## Usage

### Starting the Elevator Service

The elevator service can be started directly:

```bash
python main.py
```

Or via Docker Compose as shown above.

### Running the Simulation

The simulation script allows you to test the elevator system with various parameters:

```bash
python elevator_sim.py --users 10 --duration 300 --min-interval 5 --max-interval 30
```

Parameters:
- `--users`: Number of simulated users (default: 5)
- `--duration`: Simulation duration in seconds (default: 120)
- `--min-interval`: Minimum time between user requests in seconds (default: 5)
- `--max-interval`: Maximum time between user requests in seconds (default: 20)
- `--url`: Elevator service URL (default: http://localhost:8002)
- `--verbose`: Enable detailed logging

### API Endpoints

The elevator service exposes the following RESTful endpoints:

- `GET /state`: Get the current state of the elevator
- `GET /floor`: Get the current floor of the elevator
- `POST /go/{floor}`: Go to your desired floor from inside the elevator
- `POST /{floor}/up`: Call the elevator from outside the elevator to go up from current floor
- `POST /{floor}/down`: Call the elevator from outside the elevator to go down from current floor
- `POST /simulation/start`: Start the simulation
- `POST /simulation/stop`: Stop the simulation
- `POST /simulation/status`: Status of the simulation

## Architecture

The system follows a client-server architecture:

1. **Redis Database**: Stores elevator state, floor requests, and system configuration
2. **FastAPI Service**: Processes requests and manages elevator logic
3. **Simulation Client**: Simulates user behavior by making API calls to the service

### State Management

Elevator state is stored in Redis with the following structure:

- `current_floor`: Current floor position of the elevator
- `state`: Current operational state (idle, going up, going down, etc.)
- `up`: Sorted set of floors requested in the up direction
- `down`: Sorted set of floors requested in the down direction

## Development

### Project Structure

```
elevator-system/
├── docker-compose.yml      # Docker configuration
├── pyproject.toml          # Python package configuration
├── README.md               # This file
├── elevator_sim.py         # Simulation script
├── service.py              # Elevator service implementation
```

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.


The README.md provides a comprehensive overview of your elevator system project, including:

1. **Project Overview**: A clear description of what the system does
2. **Features**: Highlights of the key functionality
3. **Installation Instructions**: Step-by-step setup guide
4. **Usage Examples**: How to run the service and simulation
5. **API Documentation**: Details of the available endpoints
6. **Architecture**: High-level design of the system
7. **Development Information**: Project structure and testing

The markdown is formatted cleanly with proper headings, code blocks, and lists to ensure readability. The structure follows standard README conventions, making it easy for new users to understand how to set up and use your elevator system.

You can place this file in the root directory of your project to provide documentation for users and contributors.
