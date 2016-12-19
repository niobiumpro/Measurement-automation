class gpib_controler:

    def __str__(self):
        return 'GPIB controler, address {0}, GPIB board {1}'.format(self.gpib_address, self.gpib_board)

    def __repr__(self):
        return 'GPIB controler, address {0}, GPIB board {1}'.format(self.gpib_address, self.gpib_board)

    def __init__(self):
        self.gpib_address = 0
        self.gpib_board = 0
        print('GPIB controler initialized.')
        print('GPIB controler address: {0}'.format(self.gpib_address))
        print('GPIB controler board: {0}'.format(self.gpib_board))

    def __del__(self):
        print('GPIB controler released')


class instr:

    def __init__(self):
        self.id = 1
        print('Instrument initialized')

    def set_gpib_address(self, gpib_address):
        self.gpib_address = gpib_address
        print('Instrument GPIB address: {0}'.format(self.gpib_address))

    def __del__(self):
        print('Instrument released')        