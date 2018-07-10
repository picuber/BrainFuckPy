"""
This is a BrainFuck interpreter, with infinite bi-directional band and\
arbitrary sized cells.

It takes a BrainFuck program as a argument, input from stdin and outputs to st\
dout. Anything in the program that is not +-.,[]<> will be ignored and can be \
used as comments. It can either run step by step (each time printing the band,\
 position and current program position to stderr.

It has two modes: char-mode and int-mode. char-mode prints the band values as
unicode characters, int-mode prints them as integers


Exit codes:
    0: exited without errors
    -1: invalid code (loop brackets are not balanced)
    -2: read unexpected EOF
    -3: KeyboardInterrupt
"""

import sys
import argparse

"""TODO
    - IntBaseReadMode base 64
"""


class PrintMode:
    """handles output format.
    This will print ints.
    Inherit from this class to override the dot method.
    """

    change_message = "Now printing integers (base 10)\n"

    def __init__(self, file=sys.stdout):
        self.file = file

    def dot(self, value):
        """print the given value as integer in base 10

        :value: (int) the value to print
        """
        self.file.write(str(value) + ";")
        self.file.flush()


class CharPrintMode(PrintMode):
    """handles output format.z
    This will print chars
    Falls back to '█' if the value is not in range
    """

    change_message = "Now printing characters\n"

    def __init__(self, file=sys.stdout):
        super().__init__(file)

    def dot(self, value):
        """print the given value as char
        Falls back to '█' if the value is not in range

        :value: (int) the value to print
        """
        try:
            char = chr(value)
        except (OverflowError, ValueError):
            char = '█'
        self.file.write(char)
        self.file.flush()


class IntBasePrintMode(PrintMode):
    """handles output format.
    This will print chars
    Falls back to '?' if the value is not in range
    """

    @property
    def change_message(self):
        return "Now expecting integers (base {!s}) one per line\n".format(
                self.base)

    def __init__(self, base=10, file=sys.stdout):
        super().__init__(file)
        if 36 < base < 2 and base != 64:
            raise ValueError("base must be between 2 and 36 inclusive or 64")
        self.base = base

    def dot(self, value):
        """print the given value as int is base self.base

        :value: (int) the value to print
        """
        self.file.write(self.baseN(value, self.base) + ";")
        self.file.flush()

    @staticmethod
    def digits(base):
        """gets the string of digits for the given base
        :base: (int)
        :return: ((str, str, str)) a tupel (prefix, digits, suffix)
        """
        if 2 <= base <= 36:
            return ("", "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ", "")
        elif base == 64:
            return ("",
                    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz+/",
                    "=")
        else:
            raise ValueError("base must be between 2 and 36 inclusive or 64")

    @classmethod
    def baseN(cls, number, base):
        digits = cls.digits(base)
        if number == 0:
            return digits[1][0]
        string = digits[0]
        while number:
            string = digits[1][number % base] + string
            number //= base
        string += digits[2]
        return string


class ReadMode:
    """handles input format.
    Read ints in base 10 linewise
    Inherit from this class to override the comma method.
    """

    change_message = "Now expecting integers (base 10) one per line\n"

    def __init__(self, file=sys.stdin):
        self.file = file

    def comma(self):
        """read the next line and parse to int
        retry until we have a valid int
        """
        value = None
        while value is None:
            if self.file is sys.stdin:
                print("int(10), ", end='', file=sys.stderr, flush=True)

            uin = self.file.readline()
            if not uin:
                print("\nERROR: Read EOF. Cannot continue. Exiting...",
                      file=sys.stderr, flush=True)
                exit(-2)
            uin = uin.strip()

            try:
                value = int(uin)
            except ValueError:
                print("Please enter an integer base 10", file=sys.stderr)
                value = None
                continue
        return value


class CharReadMode(ReadMode):
    """handles input format
    Read chars charwise
    """

    change_message = "Now expecting characters\n"

    def __init__(self, file=sys.stdin):
        super().__init__(file)

    def comma(self):
        """read the next char"""
        user_input = self.file.read(1)
        if not user_input:
            print("\nERROR: Read EOF. Cannot continue. Exiting...",
                  file=sys.stderr, flush=True)
            exit(-2)
        return ord(user_input)


class IntBaseReadMode(ReadMode):
    """handles input format.
    Reads ints in given base linewise
    """

    @property
    def change_message(self):
        return "Now expecting integers (base {!s}) one per line\n".format(
                self.base)

    def __init__(self, base=10, file=sys.stdin):
        super().__init__(file)
        if 36 < base < 2:
            raise ValueError("base must be between 2 and 36 inclusive")
        self.base = base

    def comma(self):
        """read the next line and parse to int
        retry until we have a valid int of the given base
        """
        value = None
        while value is None:
            if self.file is sys.stdin:
                print("int(" + str(self.base) + "), ",
                      end='', file=sys.stderr, flush=True)

            uin = self.file.readline()
            if not uin:
                print("\nERROR: Read EOF. Cannot continue. Exiting...",
                      file=sys.stderr, flush=True)
                exit(-2)
            uin = uin.strip()

            try:
                value = int(uin, self.base)
            except ValueError:
                if self.file is sys.stdin:
                    print("Please enter an integer base " + str(self.base),
                          file=sys.stderr)
                value = None
                continue
        return value


class DebugMode:
    """handles the debug mode
    This the no-debug.
    Inherit from this class to override the debug behaviour.
    """

    change_message = "Exited debugger\n"

    def __init__(self, bf=None, inf=sys.stdin, outf=sys.stdout):
        """
        :bf: (BrainFuck)
        :inf: (File) where to read commands
        :outf: (File) where to write responses
        """
        self.bf = bf
        self.inf = inf
        self.outf = outf

    def debug(self, end=False):
        """handles the debugger console

        :end: (bool) whether the program has already stopped
        :return: (tupel) [0]: what to do, [...] arguments
            s: steps, [1]: number of steps
            p: run unitil position, [1]: position
            r: restart
        """
        if (self.bf._pointer >= len(self.bf._program)):
            exit(0)
        return ('s', 1)


class DefaultDebugMode(DebugMode):
    """handles the debug mode
    This is the default debug mode
    """

    _DBUGGER_HELP_MESSAGE = """Debugger help:
    h, ?:    show this help
    i <n>:   expect input as ints of base n (default: 10)
                 allowed range: 2-36,64
                 if n < 2 then n will be set to 2
                 if n > 36 then n will be set to 64
    c:       expect input as chars
    I <n>:   print in ints of base n (default: 10)
                 allowed range: 2-36
                 if n < 2 then n will be set to 2
                 if n > 36 then n will be set to 36
    C:       print in chars
    s <n>:   step n times (default: 1)
    p <n>:   step until program pointer is at position n
    p $;     step until the end of the program (without exiting the debugger)
    t:       toggle show state
    > <n>:   set until how far the band is shown to the right (default: 25)
    < <n>:   set until how far the band is shown to the left (default: 25)
    ) <n>:   set until how far the program is shown to the right (default: 25)
    ( <n>:   set until how far the program is shown to the left (default: 25)
    r:       reset execution
    e:       exit debugger
    q:       exit\n"""

    def __init__(self, bf, args, inf=sys.stdin, outf=sys.stdout):
        """
        :args: (argparse.Namespace) the command line arguments, containing file
        infos
        """
        super().__init__(bf, inf, outf)
        self.args = args
        self.show_state = True
        self.band_left = 25
        self.band_right = 25
        self.prog_left = 25
        self.prog_right = 25

    def _print_state(self):
        self.outf.write("state: "
                        + str(self.bf._band.lband[self.band_left::-1]) + " >>>"
                        + str(self.bf._band.rband[0:1]) + "<<< "
                        + str(self.bf._band.rband[1:self.band_right + 1])
                        + '\n')
        i = self.bf._pointer
        self.outf.write("state: "
                        + self.bf._program[max(0, i - self.prog_left):i] + " ("
                        + self.bf._program[i:i + 1] + ") "
                        + self.bf._program[i+1:i + self.prog_right + 1]
                        + '\n')
        self.outf.write("state: program pointer = "
                        + str(self.bf._pointer)
                        + '\n')
        self.outf.write("state: step counter = "
                        + str(self.bf._counter)
                        + '\n')
        self.outf.flush()
        pass

    def debug(self, end=False):
        """handles the debugger console

        :end: (bool) whether the program has already stopped
        :return: (tupel) [0]: what to do, [...] arguments
            s: steps, [1]: number of steps
            p: run unitil position, [1]: position

        """
        if self.show_state:
            self._print_state()

        if self.inf is sys.stdin:
            print("debug> ", end='', file=sys.stderr, flush=True)

        uin = self.inf.readline()
        if not uin:
            print("\nERROR: Read EOF. Cannot continue. Exiting...",
                  file=sys.stderr, flush=True)
            exit(-2)
        uin = uin.strip()

        if not uin:
            return ('s', 1)
        elif uin[0] == '?' or uin[0] == 'h':
            self.outf.write(self._DBUGGER_HELP_MESSAGE)
            return ('s', 0)
        elif uin[0] == 'i':
            try:
                value = int(uin[1:])
            except ValueError:
                value = 10
            value = max(value, 2)
            value = min(value, 36)
            if self.bf.set_read_mode(IntBaseReadMode(value, args.inf)):
                self.outf.write(self.bf._read_mode.change_message)
            return ('s', 0)
        elif uin[0] == 'c':
            if self.bf.set_read_mode(CharReadMode(args.inf)):
                self.outf.write(self.bf._read_mode.change_message)
            return ('s', 0)
        elif uin[0] == 'I':
            try:
                value = int(uin[1:])
            except ValueError:
                value = 10
            value = max(value, 2)
            if value > 36:
                value = 64
            if self.bf.set_print_mode(IntBasePrintMode(value, args.outf)):
                self.outf.write(self.bf._print_mode.change_message)
            return ('s', 0)
        elif uin[0] == 'C':
            if self.bf.set_print_mode(CharPrintMode(args.outf)):
                self.outf.write(self.bf._print_mode.change_message)
            return ('s', 0)
        elif uin[0] == 's':
            try:
                return ('s', int(uin[1:]))
            except ValueError:
                pass
            return ('s', 1)
        elif uin[0] == 'p':
            tail = uin[1:].strip()
            if len(tail) > 0 and tail[0] == '$':
                return('p', len(self.bf._program))
            try:
                value = int(tail)
            except ValueError:
                self.outf.write("Argument for command p has to be an integer "
                                "in base 10 or $\n")
                return ('s', 0)
            return ('p', value)
        elif uin[0] == 't':
            self.show_state = not self.show_state
        elif uin[0] == 'r':
            args.outf.flush()
            args.debugout.flush()
            return ('r')
        elif uin[0] == 'e':
            if self.bf.set_debug_mode(DebugMode(self.bf)):
                self.outf.write(self.bf._debug_mode.change_message)
            return ('s', 0)
        elif uin[0] == 'q':
            self.outf.write("Exiting...")
            exit(0)
        else:
            self.outf.write("Not a recognized command\n")
            return ('s', 0)


class Band:
    """A storage band for a BrainFuck mashine"""

    def __init__(self):
        self.reset()

    def left(self):
        """go one cell to the left"""
        if not self.lband:
            self.lband = [0]
        self.rband[0:0] = self.lband[0:1]   # insert first element of l to r
        self.lband[0:1] = []                 # remove first element of l

    def right(self):
        """go one cell to the right"""
        self.lband[0:0] = self.rband[0:1]   # insert first element of r to l
        self.rband[0:1] = []    # remove first element of r
        if self.rband == []:
            self.rband = [0]

    def minus(self):
        """decrease current cell by one"""
        self.rband[0] -= 1

    def plus(self):
        """increase current cell by one"""
        self.rband[0] += 1

    def get(self):
        """return value of current cell"""
        return self.rband[0]

    def set(self, value=0):
        """set value of current cell

        :value: the value to set the current cell to, if not given reset cell
        """
        self.rband[0] = value

    def reset(self):
        """reset band
        rband is the band right of the pointer as a stack
        lband is the band left of the pointer as a stack
        rband[0] is the pointer position
        """
        self.rband = [0]
        self.lband = []


class BrainFuck:
    """
    An BrainFuck interpreter.
    It has:
        - infinite bi-directional band
        - arbitrary sized cells
        - infinite loop netsing
        - expandable print and read modes
        - option to run in debug mode (also custom debugger)
    """

    valid_chars = ['+', '-', '.', ',', '<', '>', '[', ']']

    def __init__(self,
                 program=None,
                 debug_mode=None,
                 print_mode=PrintMode(),
                 read_mode=ReadMode()
                 ):
        """
        _program is the program to run
        _pointer is the position of the next executing command in the program
        _counter counts the number of past steps
        _loop_stack is a record of the starting positions of the nested loops
        _band is the storage band
        _print_mode handles the output format
        _read_mode handles the input format
        _debug_mode handles the debugger
        """
        if program is None:
            program = self.get_program_from_stdin()
        program = self.sanitize(program)
        self.check_valid(program)

        self._program = program
        self._pointer = 0
        self._counter = 0
        self._loop_stack = []
        self._band = Band()
        self._print_mode = print_mode
        self._read_mode = read_mode
        self._debug_mode = DebugMode(self) if not debug_mode else debug_mode

    @staticmethod
    def get_program_from_stdin():
        """prompts the user to input the program on stdin, since it was not
        given via a file or as a command line argument string.
        :returns: the program read from stdin
        """
        try:
            print("Please enter the brainfuck program below. When done, "
                  "hit Ctrl-d on an empty line.", file=sys.stderr)
            print("prog> ", end='', file=sys.stderr, flush=True)
            program = ""
            for l in sys.stdin:
                print("prog> ", end='', file=sys.stderr, flush=True)
                program += l.strip()
            print("\n", file=sys.stderr, flush=True)
            return program
        except KeyboardInterrupt:
            print("\nERROR: Caught KeyboardInterrupt. Exiting...",
                  file=sys.stderr, flush=True)
            exit(-3)

    @classmethod
    def sanitize(cls, program):
        """sanatize program from invalid chars

        :program: the given brainfuck program
        :returns: the sanitize brainfuck program
        """
        sanitized = list(filter(lambda x: x in cls.valid_chars, program))
        return ''.join(sanitized)

    @staticmethod
    def check_valid(program):
        """check if loop brackets are balanced.
        if not exit
        assume the program was already sanitized from comments

        :program: the program to be check on loop bracket balance
        """
        balance = 0
        for c in program:
            if c == '[':
                balance += 1
            elif c == ']':
                balance -= 1
            if balance < 0:
                print("\nERROR: Loop brackets not balanced", file=sys.stderr,
                      flush=True)
                exit(-1)
        if balance > 0:
            print("\nERROR: Loop bracket not balanced, not enough closing",
                  file=sys.stderr, flush=True)
            exit(-1)

    def _dot(self):
        """print current cell """
        self._print_mode.dot(self._band.get())

    def _comma(self):
        """read input from stdin and override the current cell with it.
        re-try until we read an int (int-mode)
        or use the first available char (char-mode)
        """
        self._band.set(self._read_mode.comma())

    def _left(self):
        """go one cell to the left"""
        self._band.left()

    def _right(self):
        """go one cell to the right """
        self._band.right()

    def _loop(self):
        """note where the current loop starts into the loop_stack"""
        self._loop_stack[0:0] = [self._pointer]

    def _endloop(self):
        """handle the end of the loop (pop loop_stack or jump to loop start)"""
        if not self._band.get():
            self._loop_stack[0:1] = []
        else:
            self._pointer = self._loop_stack[0]

    def _nop(self):
        """do nothing"""
        pass

    def _do_step(self):
        """do the next step in the program"""
        if self._pointer >= len(self._program):
            return
        char = self._program[self._pointer]
        {
            '+': self._band.plus,
            '-': self._band.minus,
            '.': self._dot,
            ',': self._comma,
            '<': self._band.left,
            '>': self._band.right,
            '[': self._loop,
            ']': self._endloop,
        }[char]()
        self._pointer += 1
        self._counter += 1

    def set_print_mode(self, mode):
        """change the print mode

        :mode: (PrintMode) to change to
        :return: if mode was changed/set
        """
        if isinstance(mode, PrintMode):
            self._print_mode = mode
            return True
        return False

    def set_read_mode(self, mode):
        """change the read mode

        :mode: (ReadMode) to change to
        :return: if mode was changed/set
        """
        if isinstance(mode, ReadMode):
            self._read_mode = mode
            return True
        return False

    def set_debug_mode(self, mode):
        """change the debug mode

        :mode: (DebugMode) to change to
        :return: if mode was changed/set
        """
        if isinstance(mode, DebugMode):
            self._debug_mode = mode
            return True
        return False

    def run(self):
        """simulate the given program"""
        try:
            while True:
                action = self._debug_mode.debug()
                if action[0] == 's':
                    for _ in range(action[1]):
                        self._do_step()
                elif action[0] == 'p':
                    position = min(action[1], len(self._program))
                    while self._pointer < position:
                        self._do_step()
                elif action[0] == 'r':
                    self._pointer = 0
                    self._counter = 0
                    self._band.reset()
        except KeyboardInterrupt:
            print("\nERROR: Caught KeyboardInterrupt. Exiting...",
                  file=sys.stderr, flush=True)
            exit(-3)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-X", "--no-execute",
                        dest='execute',
                        action='store_false',
                        help="sanitize and validate program and print that to"
                        "stdout, but exit without running it.")
    prog = parser.add_mutually_exclusive_group()
    prog.add_argument("-p", "--program",
                      dest='prog',
                      metavar="string",
                      action='store',
                      type=str,
                      help="a string containing the brainfuck program")
    prog.add_argument("file",
                      metavar="program",
                      default=None,
                      action='store',
                      nargs='?',
                      type=argparse.FileType('r'),
                      help="the file containing the brainfuck program")
    parser.add_argument("-i", "--in",
                        dest='inf',
                        metavar="file",
                        default=sys.stdin,
                        action='store',
                        type=argparse.FileType('r'),
                        help="a file containing the inputs for ',' "
                        "commands (default: stdin)."
                        "if not set, the prompts for ,-commands are written "
                        "to stderr, so it is recommended to redirect it when "
                        "input is piped in")
    parser.add_argument("-o", "--out",
                        dest='outf',
                        metavar="file",
                        default=sys.stdout,
                        action='store',
                        type=argparse.FileType('w'),
                        help="a file to which the outputs for '.' "
                        "commands are written (default: stdout)")
    parser.add_argument("-r", "--read-int",
                        dest='read_base',
                        metavar='base',
                        default=None,
                        const=10,
                        action='store',
                        nargs='?',
                        type=int,
                        help="read input as integer (of base b) "
                        "instead of characters")
    parser.add_argument("-w", "--write-int",
                        dest='write_base',
                        metavar='base',
                        default=None,
                        const=10,
                        action='store',
                        nargs='?',
                        type=int,
                        help="print output as ;-seperated list of integers"
                        "(of base b) instead of characters")
    parser.add_argument("-d", "--dbg", "--debug",
                        dest='debug',
                        action='store_true',
                        help="run in debug mode ")
    parser.add_argument("--dbgin", "--debugin",
                        dest='debugin',
                        metavar='file',
                        default=sys.stdin,
                        action='store',
                        type=argparse.FileType('r'),
                        help="a file containing debugger commands"
                        "(one per line)")
    parser.add_argument("--dbgout", "--debugout",
                        dest='debugout',
                        metavar='file',
                        default=sys.stdout,
                        action='store',
                        type=argparse.FileType('w'),
                        help="a file to which debugger command responses are "
                        "written")
    args = parser.parse_args()

    if args.file:
        args.prog = args.file.read()

    brainfuck = BrainFuck(args.prog)

    if not args.execute:
        print(brainfuck._program, flush=True)
        exit(0)

    if args.debug:
        brainfuck.set_debug_mode(DefaultDebugMode(brainfuck,
                                                  args,
                                                  args.debugin,
                                                  args.debugout))
    if args.write_base:
        brainfuck.set_print_mode(IntBasePrintMode(args.write_base, args.outf))
    else:
        brainfuck.set_print_mode(CharPrintMode(args.outf))

    if args.read_base:
        brainfuck.set_read_mode(IntBaseReadMode(args.read_base, args.inf))
    else:
        brainfuck.set_read_mode(CharReadMode(args.inf))

    brainfuck.run()
