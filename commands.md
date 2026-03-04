## AODV Route Table Print

### TCP connection with Simulator

python3 print_route_table.py -p 4405


### Via Serial Port Connection

python3 route_table_print.py -p /dev/ttyACM0 -t 10


## SDN - Route Install 

### Via TCP Connection Testing with Simulator

python3 routeInstall.py

### via Serial Port Connection

python3 /home/raveen/aodv_route_table/routeInstall_serial.py send   --port /dev/ttyACM0   --destination 0x14   --path 0x12,0x13,0x14   --install-id 1


