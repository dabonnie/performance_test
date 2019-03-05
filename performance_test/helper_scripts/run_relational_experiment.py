"""
Script used to automate ApexAI performance test experiment creation and execution.

Required experiment parameters are

     topic
     rate
     number of publishers
     number of subscribers

Optional parameters are

    reliability
    durability
    security

Each experiment's log output is grouped by topic and optional flags. For example the following experiment command

    ros2 run performance_test perf_test --communication ROS2 --topic Struct256 --rate 7 -p1 -s5 --reliable  --transient

would be saved in the following location:

    experiment_YYYY-MM-DD_HH-MM-SS/Struct256_reliable_transient/topicStruct256_rate7_p1_s5_reliable_transient.log

This grouping is done such that the plot_relational_experiment.py module can plot each experiment using the number of
subscribers and the message rate as respective x-axes.

@author Devin Bonnie <dbbonnie@amazon.com>
"""


import argparse
import os
import signal
import subprocess
import itertools
import logging
import time
from datetime import datetime, timedelta


COMMAND_PREFIX = 'ros2 run performance_test perf_test --communication ROS2'
VALID_TOPICS = ['Array1k', 'Array4k', 'Array16k', 'Array32k', 'Array60k', 'Array1m', 'Array2m',
                'Struct16', 'Struct256', 'Struct4k', 'Struct32k', 'PointCloud512k',
                'PointCloud1m', 'PointCloud2m', 'PointCloud4m', 'PointCloud8m', 'Range', 'NavSatFix',
                'RadarDetection', 'RadarTrack']
RELIABLE_FLAG = 'reliable'
DURABILITY_FLAG = 'transient'
SECURITY_FLAG = 'with_security'


def generate_experiment_permutations(parent_path, topics, rates, num_pubs, num_subs, reliability, durability, security):
    """
    Generate all experiments from the command line arguments.

    :param parent_path: parent directory used to save experiment log files
    :param topics: list of topics (message type + size)
    :param rates:
    :param num_subs:
    :param num_pubs:
    :param reliability:
    :param durability:
    :param security:
    :return: all permutations of the experiment input arguments
    """

    r = ['']
    if reliability:
        r.append(RELIABLE_FLAG)

    d = ['']
    if durability:
        d.append(DURABILITY_FLAG)

    s = ['']
    if security:
        s.append(SECURITY_FLAG)

    experiments = []
    permutations = list(itertools.product(topics, rates, num_pubs, num_subs, r, d, s))

    for p in permutations:
        e = Experiment(parent_path, p[0], p[1], p[2], p[3], p[4], p[5], p[6])  # todo this signature is ugly
        experiments.append(e)

    return experiments


def get_date():
    """
    Return the date in the format used to log experiment files.

    :return:
    """
    d = datetime.utcnow()
    return d.strftime("%Y-%m-%d_%H-%M-%S")


class Experiment:
    """
    A class encapsulating a single experiment's options, resulting per_test command, file name, and file path.
    """

    def __init__(self, parent_path, topic, rate, num_publishers, num_subscribers, reliability, durability, security):

        self.topic = topic
        self.rate = rate
        self.num_publishers = num_publishers
        self.num_subscribers = num_subscribers
        self.reliability = reliability
        self.durability = durability
        self.security = security

        optional_params = []
        if reliability:
            optional_params.append(RELIABLE_FLAG)
        if durability:
            optional_params.append(DURABILITY_FLAG)
        if security:
            optional_params.append(SECURITY_FLAG)

        optional_filename = '' if not optional_params else ''.join(['_' + str(x) for x in optional_params])
        optional_filename.replace('with_', '')

        self.path = parent_path + '/' + topic + optional_filename

        self.file_name = self.path + '/topic' + topic + '_rate' + str(rate) + '_p' + str(num_publishers) + '_s' \
            + str(num_subscribers) + optional_filename + '.log'

        self.command = COMMAND_PREFIX + ' --topic ' + self.topic + ' --rate ' + str(self.rate) + ' -p' \
            + str(self.num_publishers) + ' -s' + str(self.num_subscribers) \
            + ('' if not optional_params else ' '.join([' --' + str(x) for x in optional_params])) + ' -l ' \
            + self.file_name

    def get_command(self):
        """
        Return the command used to execute this experiment.

        :return:
        """
        return self.command

    def get_file_name(self):
        """
        Return the file name for this experiment's log.

        :return:
        """
        return self.file_name

    def get_path(self):
        """
        Return the location where this experiment's log file will be saved.

        :return:
        """
        return self.path

    def run(self):
        """
        Executed this experiment as a non-blocking process

        :return: the process object for this experiment
        """

        print('running ' + str(self))

        # create directory for log file if it doesn't exist
        if not os.path.exists(self.path):
            os.makedirs(self.path)

        return subprocess.Popen(self.command, shell=True)

    def __str__(self):
        return self.command


class ExperimentRunner:
    """perf_test process encapsulation."""

    def __init__(self, experiment_list, parent_path, log_system_stats=False):
        """

        :param experiment_list: list of experiments to run
        :param parent_path: parent path / directory to store experiment data
        :param log_system_stats: if true then log data per log_system_stats.py
        """

        self.processes = []
        self.number_tests_executed = 0
        self.experiment_list = experiment_list
        self.log_system_stats = log_system_stats

        if not os.path.exists(parent_path):
            os.makedirs(parent_path)

        # setup logging format to log each executed test
        logging.basicConfig(filename='./' + parent_path + '/tests_executed' + '.log', filemode='w',
                            level=logging.INFO, format='%(asctime)s,%(message)s', datefmt='%Y-%m-%dT%H:%M:%S')

    def get_number_of_experiments(self):
        """
        Return the number of tests left to execute.

        :return:
        """
        return len(self.experiment_list)

    def has_commands(self):
        """
        Return true if any tests are left to execute, false otherwise.

        :return:
        """
        return len(self.experiment_list) > 0

    def run(self):
        """
        Run the embedded perf_test process. Note: this will run a single experiment at a time.

        """

        if self.has_commands():

            e = self.experiment_list.pop(0)

            # log experiment
            logging.info(e)

            if self.log_system_stats:
                print('Logging system stats')
                file_name = e.get_file_name().replace('topic', 'system_info_topic').replace('.log', '.csv')
                print(file_name)
                self.processes.append(subprocess.Popen(['python', 'log_system_stats.py', '-l', file_name]))

            # start the experiment
            self.processes.append(e.run())

            self.number_tests_executed += 1
            time.sleep(1)

        else:
            print("No more commands to run")

    def kill(self):
        """Kill the associated performance test process."""
        for p in self.processes:
            p.kill()
            subprocess.Popen('kill -9 ' + str(p.pid), shell=True)

        self.processes = []
        subprocess.Popen('pkill -9 perf_test', shell=True)


def main():
    """
    Parse command line arguments to construct and run specified experiments.

    :return:
    """
    parser = argparse.ArgumentParser(description='Run ROS2 Perf Tests')

    parser.add_argument('-p', '--period', help='Period (seconds) to run experiments (default=60)', default=60.0)
    parser.add_argument('-t', '--topics', help='Topics', choices=VALID_TOPICS, nargs='*', required=True)
    parser.add_argument("-r", "--rate", help='Message rate (Hz)', type=int, nargs='*', required=True)
    parser.add_argument("-np", "--publishers", help='Number of publishers', type=int, nargs='*', default=[1])
    parser.add_argument("-ns", "--subscribers", help='Number of subscribers', type=int, nargs='*', default=[1])
    parser.add_argument("-re", "--reliability", help='Enable reliable QOS', action='store_true')
    parser.add_argument("-d", "--durability", help='Enable transient QOS', action='store_true')
    parser.add_argument("-s", "--security", help='Enable security', action='store_true')
    parser.add_argument("-ss", "--system_stats", help="Log system (CPU, Mem) stats", action='store_true')

    parsed_arguments = parser.parse_args()

    # validate inputs
    rate = sorted(parsed_arguments.rate)
    for i in rate:
        if i <= 0:
            parser.error("rate must be greater than 0")
        else:
            break

    publishers = sorted(parsed_arguments.publishers)
    for i in publishers:
        if i <= 0:
            parser.error("publishers must be greater than 0")
        else:
            break

    subscribers = sorted(parsed_arguments.subscribers)
    for i in subscribers:
        if i < 0:
            parser.error("subscribers must be greater than or equal to 0")
        else:
            break

    period = float(parsed_arguments.period) + 1.0

    if period <= 0:
        parser.error("period must be greater than 0")

    log_system_stats = parsed_arguments.system_stats

    # ----

    path = 'experiment_' + str(get_date())
    e_list = generate_experiment_permutations(path, parsed_arguments.topics, rate, publishers, subscribers,
                                              parsed_arguments.reliability, parsed_arguments.durability,
                                              parsed_arguments.security)

    global tests_to_run
    tests_to_run = ExperimentRunner(e_list, path, log_system_stats)

    print('Executing ' + str(tests_to_run.get_number_of_experiments()) + ' tests')

    minutes, seconds = divmod(tests_to_run.get_number_of_experiments() * period, 60)
    hours, minutes = divmod(minutes, 60)

    print('Estimated time to run all tests: ' + str(hours) + ' hours ' + str(minutes) + ' minutes ' + str(
        seconds) + ' seconds')

    now = datetime.now()
    then = now + timedelta(hours=hours, minutes=minutes, seconds=seconds)

    print('Estimated completion at: ' + str(then))

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGALRM, timer_handler)
    signal.setitimer(signal.ITIMER_REAL, period, period)

    timer_handler()
    while True:
        signal.pause()


def signal_handler(_sig, _frame):
    """Signal handler to handle Ctrl-C."""

    global tests_to_run

    print('You pressed Ctrl+C! Terminating experiment. Executed ' + str(tests_to_run.number_tests_executed)
          + ' tests.')
    tests_to_run.kill()
    exit(0)


def timer_handler(_sig=None, _frame=None):
    """Signal handler to handle the timer. Kills an experiment."""

    global tests_to_run
    subprocess.Popen('pkill -9 log_system_stats.py', shell=True)
    tests_to_run.kill()  # kill the last test when the time limit has exceeded

    # run the next test
    if tests_to_run.has_commands():
        tests_to_run.run()
    else:
        print('--FINISHED--')
        exit(0)


if __name__ == "__main__":
    main()
