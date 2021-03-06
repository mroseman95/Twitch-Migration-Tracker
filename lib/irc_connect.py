import pdb
import sys
import os
import socket
import configparser

# Constants
SERVER = 'irc.chat.twitch.tv'
PORT = 6667
NICKNAME = 'mroseman'
PASSWORD = ''

BUFFER_SIZE = 2048


class IRCBadMessage(Exception):
    pass


class IRCConnection:
    """
    Used to connect to the twitch irc server and get messages, etc from
    different channels
    """

    current_dir = os.path.dirname(__file__)
    config_rel_path = '../config/irc.cfg'
    config_abs_path = os.path.join(current_dir, config_rel_path)

    section_name = 'Connection Authentication'

    def __init__(self):
        config = configparser.ConfigParser()
        config.read(self.config_abs_path)

        try:
            PASSWORD = config[self.section_name]['oauth']
        except Exception as e:
            print('one of the options in the config file has no value\n{0}:' +
                  '{1}').format(e.errno, e.strerror)
            sys.exit()

        self.IRC = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.IRC.connect((SERVER, PORT))

        self._send_data('PASS %s' % PASSWORD)
        self._send_data('NICK %s' % NICKNAME)
        self._send_data('CAP REQ :twitch.tv/membership')

    def _send_data(self, command):
        """
        sends the given command to the IRC server
        """
        self.IRC.send(bytes(command + '\r\n', 'UTF-8'))

    def _parse_line(self, line):
        """
        takes an irc message and parses it into prefix, command and args
        @return: (prefix, command, args)
        """
        prefix = ''
        if not line:
            raise IRCBadMessage("Empty line.")
        if line[0] == ':':
            try:
                prefix, line = line[1:].split(' ', 1)
            except ValueError as e:
                print(line)
                raise e
        if line.find(' :') != -1:
            line, trailing = line.split(' ', 1)
            args = line.split()
            args.append(trailing)
        else:
            args = line.split()
        command = args.pop(0)
        if not command or not args:
            raise IRCBadMessage('Improperly formatted line: {0}'.format(line))
        return prefix, command, args

    def get_channel_users(self, channel):
        """
        gets a list of users from the IRC NAMES command
        @return: a set of users from the irc (may be just OPs)
        """
        #  clear the IRC buffer
        temp = self.IRC.recv(BUFFER_SIZE)
        #  join the IRC channel
        self._send_data('JOIN #{0}'.format(channel))
        users = set()
        readbuffer = ''
        debug_lines = ''
        while True:
            readbuffer = readbuffer +\
                str(self.IRC.recv(BUFFER_SIZE).decode('UTF-8'))
            temp = str.split(readbuffer, '\n')
            # If there isn't a \n char at the end of the line then the whole
            # line wasn't received so it is popped and included in the next
            # iteration
            readbuffer = temp.pop()
            for line in temp:
                debug_lines += line + '\n'
                line = str.rstrip(line)
                # print(line)
                try:
                    _, command, args = self._parse_line(line)
                except IRCBadMessage as e:
                    pdb.set_trace()
                    print('bad IRC message received, returning empty user' +
                          'list')
                    print(e)
                    print()
                    print(debug_lines)
                    return []

                try:
                    #  if this is a response to NAMES
                    if command == '353':
                        users |= set((args[0].split(':', 1))[1].split())
                    if 'End of /NAMES list' in args[0]:
                        self._send_data('PART #{0}'.format(channel))
                        return users
                except Exception as e:
                    print('\n\n')
                    print(debug_lines)
                    raise e
                    print('\n\n')
