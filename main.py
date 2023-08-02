import click

from attention_monitoring import startSession

@click.command()
@click.option(
    '-p', '--participant_id',
    default=None,
    show_default=True,
    help='ID of participant')
def collect_data(participant_id):
    startSession(participant_id)

@click.group()
def cli():
    pass

cli.add_command(collect_data)

if __name__ == '__main__':
    cli()