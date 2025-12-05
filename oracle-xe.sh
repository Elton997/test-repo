#!/bin/bash

# Oracle XE Container Management Script
# Works with both Docker and Podman
# Usage: ./oracle-xe.sh [start|stop|logs|shell|status|remove]

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Container configuration
CONTAINER_NAME="dcim-oracle-xe"
IMAGE="docker.io/gvenzl/oracle-xe:21-slim"
ORACLE_PASSWORD="Oracle123"
ORACLE_DATABASE="ORCLPDB1"
PORT="1521"
EM_PORT="5500"
VOLUME_NAME="oracle_xe_data"

# Detect container runtime (docker or podman)
detect_runtime() {
    if command -v podman &> /dev/null; then
        RUNTIME="podman"
    elif command -v docker &> /dev/null; then
        RUNTIME="docker"
    else
        echo -e "${RED}Error: Neither Docker nor Podman is installed${NC}"
        exit 1
    fi
}

# Check if container exists
container_exists() {
    $RUNTIME ps -a --format "{{.Names}}" | grep -q "^${CONTAINER_NAME}$"
}

# Check if container is running
container_running() {
    $RUNTIME ps --format "{{.Names}}" | grep -q "^${CONTAINER_NAME}$"
}

# Start container
start_container() {
    detect_runtime
    
    if container_running; then
        echo -e "${YELLOW}Container ${CONTAINER_NAME} is already running${NC}"
        return 0
    fi
    
    echo -e "${GREEN}Starting Oracle XE container...${NC}"
    
    # Create volume if it doesn't exist
    if ! $RUNTIME volume exists $VOLUME_NAME &> /dev/null; then
        echo -e "${YELLOW}Creating volume ${VOLUME_NAME}...${NC}"
        $RUNTIME volume create $VOLUME_NAME
    fi
    
    # Remove existing stopped container if it exists
    if container_exists && ! container_running; then
        echo -e "${YELLOW}Removing existing stopped container...${NC}"
        $RUNTIME rm $CONTAINER_NAME
    fi
    
    # Start container
    $RUNTIME run -d \
        --name $CONTAINER_NAME \
        -e ORACLE_PASSWORD=$ORACLE_PASSWORD \
        -e ORACLE_DATABASE=$ORACLE_DATABASE \
        -p ${PORT}:1521 \
        -p ${EM_PORT}:5500 \
        -v $VOLUME_NAME:/opt/oracle/oradata \
        --shm-size=2g \
        --restart unless-stopped \
        $IMAGE
    
    echo -e "${GREEN}Container started${NC}"
    echo -e "${YELLOW}Waiting for Oracle database to be ready...${NC}"
    echo -e "${YELLOW}This may take 1-3 minutes on first startup...${NC}"
    
    # Wait for Oracle to be ready
    MAX_WAIT=180
    WAIT_TIME=0
    while [ $WAIT_TIME -lt $MAX_WAIT ]; do
        if $RUNTIME exec $CONTAINER_NAME healthcheck.sh &> /dev/null; then
            echo -e "\n${GREEN}Oracle database is ready!${NC}\n"
            show_connection_info
            return 0
        fi
        echo -n "."
        sleep 5
        WAIT_TIME=$((WAIT_TIME + 5))
    done
    
    echo -e "\n${YELLOW}Container started but database may still be initializing${NC}"
    echo -e "${BLUE}Check status with: ./oracle-xe.sh logs${NC}"
    show_connection_info
}

# Stop container
stop_container() {
    detect_runtime
    
    if ! container_exists; then
        echo -e "${YELLOW}Container ${CONTAINER_NAME} does not exist${NC}"
        return 0
    fi
    
    if ! container_running; then
        echo -e "${YELLOW}Container ${CONTAINER_NAME} is not running${NC}"
        return 0
    fi
    
    echo -e "${YELLOW}Stopping container ${CONTAINER_NAME}...${NC}"
    $RUNTIME stop $CONTAINER_NAME
    echo -e "${GREEN}Container stopped${NC}"
}

# Show container logs
show_logs() {
    detect_runtime
    
    if ! container_exists; then
        echo -e "${RED}Container ${CONTAINER_NAME} does not exist${NC}"
        exit 1
    fi
    
    echo -e "${YELLOW}Container logs (Ctrl+C to exit):${NC}"
    $RUNTIME logs -f $CONTAINER_NAME
}

# Enter container shell
enter_shell() {
    detect_runtime
    
    if ! container_exists; then
        echo -e "${RED}Container ${CONTAINER_NAME} does not exist${NC}"
        exit 1
    fi
    
    if ! container_running; then
        echo -e "${RED}Container ${CONTAINER_NAME} is not running${NC}"
        echo -e "${YELLOW}Start it with: ./oracle-xe.sh start${NC}"
        exit 1
    fi
    
    echo -e "${YELLOW}Entering container shell...${NC}"
    $RUNTIME exec -it $CONTAINER_NAME bash
}

# Show container status
show_status() {
    detect_runtime
    
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}  Oracle XE Container Status${NC}"
    echo -e "${BLUE}========================================${NC}\n"
    
    if ! container_exists; then
        echo -e "${YELLOW}Container:${NC} ${CONTAINER_NAME} (does not exist)"
        echo -e "${YELLOW}Status:${NC} Not created"
        return 0
    fi
    
    if container_running; then
        echo -e "${GREEN}Container:${NC} ${CONTAINER_NAME}"
        echo -e "${GREEN}Status:${NC} Running"
        echo ""
        $RUNTIME ps --filter "name=${CONTAINER_NAME}" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
    else
        echo -e "${YELLOW}Container:${NC} ${CONTAINER_NAME}"
        echo -e "${YELLOW}Status:${NC} Stopped"
    fi
    
    echo ""
    show_connection_info
}

# Remove container and volume
remove_container() {
    detect_runtime
    
    if container_running; then
        echo -e "${YELLOW}Stopping container first...${NC}"
        stop_container
    fi
    
    if container_exists; then
        echo -e "${YELLOW}Removing container ${CONTAINER_NAME}...${NC}"
        $RUNTIME rm $CONTAINER_NAME
        echo -e "${GREEN}Container removed${NC}"
    else
        echo -e "${YELLOW}Container does not exist${NC}"
    fi
    
    read -p "Remove volume ${VOLUME_NAME}? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        if $RUNTIME volume exists $VOLUME_NAME &> /dev/null; then
            $RUNTIME volume rm $VOLUME_NAME
            echo -e "${GREEN}Volume removed${NC}"
        else
            echo -e "${YELLOW}Volume does not exist${NC}"
        fi
    fi
}

# Show connection information
show_connection_info() {
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}  Connection Details${NC}"
    echo -e "${BLUE}========================================${NC}\n"
    echo -e "${GREEN}Container Name:${NC} ${CONTAINER_NAME}"
    echo -e "${GREEN}Host:${NC} localhost"
    echo -e "${GREEN}Port:${NC} ${PORT}"
    echo -e "${GREEN}Service Name:${NC} ${ORACLE_DATABASE}"
    echo -e "${GREEN}Username:${NC} system"
    echo -e "${GREEN}Password:${NC} ${ORACLE_PASSWORD}"
    echo -e "${GREEN}Enterprise Manager:${NC} http://localhost:${EM_PORT}/em"
    echo ""
    
    DB_URL="oracle+oracledb://system:${ORACLE_PASSWORD}@localhost:${PORT}/?service_name=${ORACLE_DATABASE}"
    echo -e "${YELLOW}Database URL:${NC}"
    echo -e "${BLUE}export DATABASE_URL=\"${DB_URL}\"${NC}"
    echo -e "${BLUE}export DB_URL=\"${DB_URL}\"${NC}"
    echo ""
}

# Main command handler
case "${1:-}" in
    start)
        start_container
        ;;
    stop)
        stop_container
        ;;
    logs)
        show_logs
        ;;
    shell)
        enter_shell
        ;;
    status)
        show_status
        ;;
    remove)
        remove_container
        ;;
    *)
        echo -e "${BLUE}Oracle XE Container Management${NC}\n"
        echo -e "${GREEN}Usage:${NC} $0 [command]"
        echo ""
        echo -e "${GREEN}Commands:${NC}"
        echo -e "  ${YELLOW}start${NC}    - Start Oracle XE container"
        echo -e "  ${YELLOW}stop${NC}     - Stop Oracle XE container"
        echo -e "  ${YELLOW}logs${NC}     - Show container logs"
        echo -e "  ${YELLOW}shell${NC}    - Enter container shell"
        echo -e "  ${YELLOW}status${NC}   - Show container status"
        echo -e "  ${YELLOW}remove${NC}   - Remove container and optionally volume"
        echo ""
        exit 1
        ;;
esac

