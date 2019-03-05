"""
Script to provide ancillary system data to quantify ROS2 performance testing.

@author Devin Bonnie <dbbonnie@amazon.com>
"""
import datetime
import argparse
import signal
import subprocess
import logging
import time

# hack-y
global SHOULD_RUN
SHOULD_RUN = True


def get_date():
    """Return the date in the same format used by the Apex test scripts"""

    d = datetime.datetime.utcnow()
    return d.strftime("%Y-%m-%d_%H-%M-%S")


def execute_command(command):
    """
    Execute a shell command and return its output.

    :param command:
    :return:
    """

    p = subprocess.Popen(command, stdout=subprocess.PIPE, shell=True)
    return p.communicate()


def get_system_cpu_and_memory():
    """
    Issue the command: top -b -n 1 | head -4

    :return: the results of parse_top_output
    """

    o = execute_command('top -b -n 1 | head -4')
    return parse_top_output(o)


def get_process_details(process_list=None):
    """
    Get the 'top' command details for the different input processes/
    
    :type process_list: list of processes
    :return:
    """
    to_return = []
    if process_list is not None:

        pids = []
        for p in process_list:
            pid = execute_command('pgrep ' + p)[0]
            if pid is not None and pid != '':
                pids.append(pid.rstrip())

        joined_pids = ','.join(pids)

        if len(joined_pids) > 0:
            command = 'top -b -n 1 -p ' + joined_pids + ' | tail -n +8'
            o = execute_command(command)
            to_return += parse_process_output(o)

        # populate with empty info
        if len(to_return) < len(process_list):
            to_return += ['', -1, -1, -1, -1]

    return to_return


def parse_top_output(output_from_top):
    """
    Parse the output of the command: top -b -n 1 | head -4

    :param output_from_top:
    :return: a list containing the date, user cpu %, system cpu %, and memory used
    """

    # todo could return a named tuple
    user_cpu = -1
    system_cpu = -1
    memory_used = -1

    lines = str(output_from_top).split('\\n')

    if len(lines) >= 2:
        cpu_info = lines[2].replace('  ', ' ').split(' ')
        # todo validate length
        user_cpu = cpu_info[1]
        system_cpu = cpu_info[3]

    if len(lines) >= 3:
        mem_info = lines[3].split(', ')
        # todo validate length
        memory_used = mem_info[2][:-5]

    # todo return a class that implements a toString representation and can construct the data from a string
    # json_data = {'utc_timestamp': get_date(), 'user_cpu_percent': user_cpu, 'system_cpu_percent': system_cpu,
    #              'memory_used_mb': memory_used}
    return [get_date(), user_cpu, system_cpu, memory_used]


def parse_process_output(output):
    """
    Parse the output of a process from the 'top' utility.

    :return:
    """

    lines = str(output).replace('(\'', '').split('\\n')

    to_return = []
    for line in lines:

        split_line = line.split()

        if len(split_line) < 10:
            continue
        else:
            to_return.append(split_line[5])  # virtual mem
            to_return.append(split_line[6])  # physical mem
            to_return.append(split_line[8])  # % cpu
            to_return.append(split_line[9])  # % mem

    return to_return


def log_system_cpu_and_memory(process_list=None):
    """

    :param process_list:
    :return:
    """
    m = get_system_cpu_and_memory()
    n = []
    if process_list is not None:
        n = get_process_details(process_list)

    logging.info(','.join(m + n))


def handle_stop(_signum, _frame):
    """
    If SIGTERM or SIGINT are caught then stop logging

    :return:
    """

    global SHOULD_RUN
    SHOULD_RUN = False
    print('exiting logging')
    exit(0)


def test_get_system_cpu_and_memory():
    """
    Sanity check to verify parsing.

    :return:
    """

    # ec2 instance
    ec2 = 'top - 22:05:41 up 3 days,  3:06,  6 users,  load average: 0.00, 0.00, 0.00\\n' \
          + 'Tasks: 231 total,   1 running, 132 sleeping,   0 stopped,   0 zombie\\n' \
          + '%Cpu(s):  0.3 us,  0.0 sy,  0.0 ni, 99.7 id,  0.0 wa,  0.0 hi,  0.0 si,  0.0 st\\n' \
          + 'KiB Mem : 30853324 total, 20744660 free,   345192 used,  9763472 buff/cache\\n'

    # ubuntu 18 laptop
    instance = 'top - 10:27:04 up  1:44,  3 users,  load average: 1.06, 1.24, 1.74\\n' \
               + 'Tasks: 262 total,   1 running, 198 sleeping,   0 stopped,   0 zombie\\n' \
               + '%Cpu(s): 43.1 us,  5.0 sy,  0.0 ni, 51.8 id,  0.0 wa,  0.0 hi,  0.0 si,  0.0 st\\n' \
               + 'KiB Mem : 15818816 total,  8008684 free,  1107180 used,  6702952 buff/cache\\n' \
               + 'KiB Swap:  8003580 total,  8003580 free,        0 used. 14085324 avail Mem'

    i = 'top - 15:43:18 up 19 days,  7:00,  3 users,  load average: 1.07, 1.11, 1.09\\n' \
        + 'Tasks: 289 total,   1 running, 226 sleeping,   0 stopped,   0 zombie\\n' \
        + '%Cpu(s):  4.3 us,  2.0 sy,  0.0 ni, 93.4 id,  0.1 wa,  0.0 hi,  0.1 si,  0.0 st\\n' \
        + 'KiB Mem : 15818816 total, 10788060 free,  1136768 used,  3893988 buff/cache"\\n' \

    # print(parse_top_output(ec2))
    # print(parse_top_output(instance))
    print(parse_top_output(i))


def test_get_process_details():
    """

         1565 crush  20   0 1710900  42748  16096 S  20.0  0.3   0:21.41 perf_test
         1562 crush  20   0  135180  37592  12572 S   0.0  0.2   0:00.65 ros2


    :return:
    """
    test = ' 1565 crush  20   0 1710900  42748  16096 S  20.0  0.3   0:21.41 perf_test\\n' \
           + ' 1562 crush  20   0  135180  37592  12572 S   0.0  0.2   0:00.65 ros2'

    print(parse_process_output(test))


# todo keys should be static vars
def get_header(process_list=None):
    header = ['timestamp', 'user_cpu_%', 'system_cpu_%', 'memory_used_kb']
    if process_list is not None:
        for p in process_list:
            header.append('virtual_memory_' + p)
            header.append('physical_memory_' + p)
            header.append('cpu_%_' + p)
            header.append('mem_%_' + p)

    return ','.join(header)


def main():

    global SHOULD_RUN

    parser = argparse.ArgumentParser(description='Log system information (CPU, memory, etc) when running ROS2 tests')
    parser.add_argument('-l', '--log_file_name', help="The name of the file to use for logging data",
                        default="system_info_" + get_date() + '.csv')
    parser.add_argument('-p', '--period', help='Period (seconds) to run experiments (default=2)', default=2)
    parser.add_argument('-pid', '--process_list', help="List of processes to monitor", nargs='*',
                        default=['perf_test', 'ros2'])

    parsed_arguments = parser.parse_args()

    logging.basicConfig(filename=parsed_arguments.log_file_name, filemode='w', level=logging.INFO, format='%(message)s')

    signal.signal(signal.SIGTERM, handle_stop)
    signal.signal(signal.SIGINT, handle_stop)

    # setup logging header
    logging.info(get_header(parsed_arguments.process_list))

    print("Starting logging")
    while SHOULD_RUN:
        log_system_cpu_and_memory(parsed_arguments.process_list)
        time.sleep(float(parsed_arguments.period))
    print("Stopping logging")


if __name__ == "__main__":
    test_get_system_cpu_and_memory()
