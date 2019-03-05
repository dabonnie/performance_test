"""
Script to plot data recorded by the log_system_stats.py module. This will output multiple plots into a single pdf.

@author Devin Bonnie <dbbonnie@amazon.com>
"""

import argparse
import matplotlib
# allow use from the command line with a non interactive backend (https://matplotlib.org/faq/howto_faq.html)
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import os
import time
from datetime import datetime, timedelta
import pandas as pd
import matplotlib.backends.backend_pdf

DATE_FORMAT = "%Y-%m-%d_%H-%M-%S"


def parse_file_into_data_frame(file_to_open):
    """
    Open a file, read the lines, parse each line, and return the data to plot.

    :param file_to_open: the file you want to parse
    :return: a pandas.Dataframe
    """

    data_frame = pd.read_csv(file_to_open, sep=",", engine='python')
    return data_frame


def parse_line(line_to_parse):
    """
    Expected input: 2019-02-13T11:57:03,23.9,3.1,15818,117 via log_system_stats.py

    :param line_to_parse:
    :return: list of the form [utc timestamp, usr % cpu, sys % cpu, used mem MB]
    """

    parsed = line_to_parse.rstrip().split(",")
    # expect 4 entries
    if len(parsed) < 4:
        # todo handle plotting with known bad values
        return None, None, None, None

    parsed[0] = parsed[0].replace('\"', '').replace('[', '').replace('\'', '')
    for i in range(1, 4):
        parsed[i] = float(parsed[i].replace(' ', '').replace('\'', ''))

    return parsed


def plot(axis, x_data, y_data, param_dict, plot_label=''):
    """
    Plot helper function per matplotlib coding styles:
     https://matplotlib.org/tutorials/introductory/usage.html#sphx-glr-tutorials-introductory-usage-py

    :param axis:
    :param x_data:
    :param y_data:
    :param param_dict:
    :param plot_label:
    :return:
    """

    out = axis.plot(x_data, y_data, label=plot_label, **param_dict)
    return out


def plot_a(axis, x_data, data_frame_column, plot_label=''):
    """
    Plotter helper function

    :param axis:
    :param x_data:
    :param data_frame_column:
    :param plot_label:
    :return:
    """

    plot(axis, x_data, data_frame_column, {'linewidth': 1.2}, plot_label=plot_label)


def axis_legend_labels(axis, data_dict):
    """
    Provide relevant statistics for the input axis and data dictionary.

    :param axis:
    :param data_dict: a dictionary where the key is the data descriptor and the value is a Dataframe column for the key.
    :return:
    """

    stats_string = ''
    for k, v in data_dict.items():

        mean = v.mean()
        max = v.max()

        if len(v) > 1:
            std = v.std()
        else:
            std = None

        stats_string += k + ' mean=' + '{0:.2f}'.format(mean) \
                        + '\n' + k + ' max=' + '{0:.2f}'.format(max) \
                        + (' \n' + k + ' std dev=' + '{0:.2f}'.format(std) if std is not None else '') + '\n\n'

    axis.text(1.025, -0.1, stats_string, fontsize=6, horizontalalignment='left', transform=axis.transAxes)


def plot_cpu_and_mem(data_frame, plot_title=None):
    """
    Plot the system cpu, user cpu, and memory used.

    :param plot_title:
    :param data_frame:
    :return: the plotted figure
    """

    plt.style.use('ggplot')
    figure_1, (axis_1, axis_2) = plt.subplots(2, 1)

    d = [i for i in range(0, len(data_frame['timestamp']))]

    # cpu plot ---------------------------------------------------------------------------------------------------------

    plot_a(axis_1, d, data_frame['user_cpu_%'], plot_label='User')
    plot_a(axis_1, d, data_frame['system_cpu_%'], plot_label='System')

    axis_1.set_ylabel("% CPU")

    axis_legend_labels(axis_1, {'usr_cpu': data_frame['user_cpu_%'], 'system_cpu': data_frame['system_cpu_%']})

    axis_1.legend(loc='center left', bbox_to_anchor=(1, 0.8))

    # memory plot ------------------------------------------------------------------------------------------------------

    # convert to megabytes
    data_frame['memory_used_kb'] = data_frame['memory_used_kb'] / 1000.0

    plot_a(axis_2, d, data_frame['memory_used_kb'], plot_label='Memory Used')

    axis_2.set_ylabel('Megabytes')
    axis_2.legend(loc='center left', bbox_to_anchor=(1, 0.8))

    axis_legend_labels(axis_2, {'memory_used_kb': data_frame['memory_used_kb']})

    # time formatting --------------------------------------------------------------------------------------------------

    start_t = data_frame['timestamp'][0]
    end_t = data_frame['timestamp'][len(data_frame['timestamp']) - 1]  # -1 is not valid for some reason

    period = time.mktime(datetime.strptime(end_t, DATE_FORMAT).timetuple()) - \
             time.mktime(datetime.strptime(start_t, DATE_FORMAT).timetuple())
    duration = time.mktime(datetime.strptime(end_t, DATE_FORMAT).timetuple()) - \
               time.mktime(datetime.strptime(start_t, DATE_FORMAT).timetuple())

    plt.xlabel('Time\nSample Period=' + str(timedelta(seconds=period)) + ', Experiment Duration=' + str(
        timedelta(seconds=duration)) +
               '\n' + str(start_t) + '--' + str(end_t), fontsize=12)

    if plot_title is not None:
        plt.suptitle(plot_title)

    plt.tight_layout()
    plt.subplots_adjust(top=0.9)

    # plt.show()

    return figure_1


# todo these keys should really come from plot_system_stats
def plot_process_info(data_frame, exclude_keys=None):
    """
    Plot each processes virtual memory, physical memory, and percent cpu.

    :param data_frame: data frame containing virtual mem, physical mem, and cpu %
    :param key_filter: keys to exclude in processing data
    :return: the plotted figure(s)
    """

    if exclude_keys is None:
        exclude_keys = ['timestamp', 'user_cpu_%', 'system_cpu_%', 'memory_used_kb']

    to_return = []
    process_keys = []

    for key in data_frame.keys():
        if key not in exclude_keys:
            process_keys.append(key)

    # process in groups of 4: virtual mem, physical mem, % cpu, %mem
    for i in range(0, len(process_keys), 4):
        virtual_key = process_keys[i]
        physical_key = process_keys[i + 1]
        process_cpu = process_keys[i + 2]
        # ignoring % mem for now as didn't find useful

        plt.style.use('ggplot')

        figure_1, (axis_1, axis_2) = plt.subplots(2, 1)

        d = [i for i in range(0, len(data_frame['timestamp']))]

        # cpu ----------------------------------------------------------------------------------------------------------

        plot_a(axis_1, d, data_frame[process_cpu], plot_label=process_cpu)

        axis_legend_labels(axis_1, {process_cpu: data_frame[process_cpu]})
        axis_1.legend(loc='center left', bbox_to_anchor=(1, 0.8))
        axis_1.set_ylabel("% CPU")

        # memory -------------------------------------------------------------------------------------------------------

        data_frame[virtual_key] = data_frame[virtual_key] / 1000.0
        data_frame[physical_key] = data_frame[physical_key] / 1000.0

        plot_a(axis_2, d, data_frame[virtual_key], plot_label=virtual_key)
        plot_a(axis_2, d, data_frame[physical_key], plot_label=physical_key)

        axis_2.set_ylabel("Megabytes")

        axis_legend_labels(axis_2, {virtual_key: data_frame[virtual_key], physical_key: data_frame[physical_key]})
        axis_2.legend(loc='center left', bbox_to_anchor=(1, 0.8))

        plt.suptitle('Process ' + virtual_key.replace('virtual_memory_', ''))  # hardcoded, not great....
        plt.tight_layout()
        plt.subplots_adjust(top=0.9)
        to_return.append(figure_1)

        #plt.show()

    return to_return


def parse_and_plot_file(file_to_parse, file_to_save):
    """
    Parse each system stat file and plot the system + process information into a single pdf.

    :param file_to_save:
    :param file_to_parse:
    :return:
    """

    with matplotlib.backends.backend_pdf.PdfPages(file_to_save) as pdf:
        data_frame = parse_file_into_data_frame(file_to_parse)
        figure_1 = plot_cpu_and_mem(data_frame, plot_title=file_to_parse.split('/')[-1].split('.')[0])
        pdf.savefig(figure_1)
        figures = plot_process_info(data_frame)
        print('Saving ' + file_to_save)
        for f in figures:
            pdf.savefig(f)
        plt.clf()


def main():
    """
    Read all files in the current directory and only attempt to parse + plot the files with the 'csv' extension.

    :return:
    """

    parser = argparse.ArgumentParser(description='Plot System Info')
    parser.add_argument('-d', '--directory', help='base directory containing all topic subdirectories'
                                                  + '(output of run_experiment.py)', default=".")
    args = parser.parse_args()

    base_dir = args.directory

    if not os.path.isdir(base_dir):
        raise ValueError('input directory is not valid: ' + base_dir)

    for root, dirs, files in os.walk(base_dir):
        for file in files:
            if ".csv" in file and 'system' in file:
                print('Parsing ' + os.path.join(root, file))
                parse_and_plot_file(os.path.join(root, file), os.path.join(root, file).replace('.csv', '.pdf'))
            # else:
            #     print('Skipping ' + file)


if __name__ == "__main__":
    main()
