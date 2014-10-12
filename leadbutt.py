"""
Usage:
  leadbutt [options]

Options:
  -h --help                   Show this screen.
  -c FILE --config-file=FILE  Path to a YAML configuration file [default: config.yaml].
  -p INT --period INT         Period length, in minutes [default: 1]
  -n INT                      Number of data points to get [default: 5]
"""
from calendar import timegm
import datetime
import sys

from docopt import docopt
import boto.ec2.cloudwatch
import yaml


DEFAULT_REGION = 'us-east-1'


def get_config(config_file):
    """Get configuration from a file."""
    def load(fp):
        try:
            return yaml.load(fp)
        except yaml.YAMLError as e:
            sys.stderr.write(unicode(e))  # XXX python3
            sys.exit(1)  # TODO document exit codes

    if config_file == '-':
        return load(sys.stdin)
    with open(config_file) as fp:
        return load(fp)


def output_results(results, metric):
    """
    Output the results to stdout.

    TODO: add AMPQ support for efficiency
    """
    formatter = ('cloudwatch.%(Namespace)s.%(dimension)s.%(MetricName)s'
        '.%(Statistics)s.%(Unit)s')
    context = dict(
        metric,
        dimension=metric['Dimensions'].values()[0],
    )
    for result in results:
        # get and then sanitize metric name
        metric_name = (formatter % context).replace('/', '.').lower()
        print metric_name,
        print result[metric['Statistics']],
        print timegm(result['Timestamp'].timetuple())


def main(config_file, period, count, **kwargs):
    config = get_config(config_file)

    # TODO use auth from config if exists
    region = config.get('region', DEFAULT_REGION)
    conn = boto.ec2.cloudwatch.connect_to_region(region)
    for metric in config['metrics']:
        end_time = datetime.datetime.utcnow()
        start_time = end_time - datetime.timedelta(seconds=period * count)
        results = conn.get_metric_statistics(
            period,  # minimum: 60
            start_time,
            end_time,
            metric['MetricName'],  # RequestCount
            metric['Namespace'],  # AWS/ELB
            metric['Statistics'],  # Sum
            dimensions=metric['Dimensions'],
            unit=metric['Unit'],
        )
        output_results(results, metric)


if __name__ == '__main__':
    options = docopt(__doc__)
    # help: http://boto.readthedocs.org/en/latest/ref/cloudwatch.html#boto.ec2.cloudwatch.CloudWatchConnection.get_metric_statistics
    config_file = options.pop('--config-file')
    period = int(options.pop('--period')) * 60
    count = int(options.pop('-n'))
    main(config_file, period, count, **options)