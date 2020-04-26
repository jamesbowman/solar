import time
from renogy_rover import RenogyRover

if __name__ == "__main__":
    portname="/dev/serial/by-id/usb-FTDI_FT232R_USB_UART_A9GIWNYB-if00-port0"
    rover = RenogyRover(portname, 1)
    print([
        int(time.time()),
        rover.battery_percentage(),
        rover.battery_voltage(),
        round(rover.solar_voltage() * rover.solar_current(), 2)
    ])
