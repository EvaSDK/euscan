import os

from django.conf import settings


def _launch_command(cmd, logger=None):
    """
    Helper for launching shell commands inside tasks
    """
    import sys
    import subprocess
    import select

    fp = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    mask = select.EPOLLIN | select.EPOLLHUP | select.EPOLLERR

    epoll = select.epoll()
    epoll.register(fp.stdout.fileno(), mask)
    epoll.register(fp.stderr.fileno(), mask)

    if logger:
        info, error = logger.info, logger.error
    else:
        info = lambda x: sys.stdout.write(x + '\n')
        error = lambda x: sys.stderr.write(x + '\n')

    try:
        exited = False
        while not exited:
            events = epoll.poll(1)
            for fileno, event in events:
                if event & select.EPOLLIN:
                    if fileno == fp.stdout.fileno():
                        source, out = fp.stdout, info
                    else:
                        source, out = fp.stderr, error
                    line = source.readline().rstrip('\n')
                    out("%s[%s]: %s" % (cmd[0], fp.pid, line))
                elif event & (select.EPOLLERR | select.EPOLLHUP):
                    exited = True
    finally:
        epoll.close()

    fp.wait()


def emerge_sync(logger):
    """
    Launches an emerge --sync
    """
    cmd = ["emerge", "--sync", "--root", settings.PORTAGE_ROOT,
           "--config-root", settings.PORTAGE_CONFIGROOT]
    return _launch_command(cmd, logger)


def layman_sync(logger, cache=True):
    """
    Syncs Layman repos
    """
    from layman import Layman
    import shutil

    l = Layman(config=settings.LAYMAN_CONFIG)

    installed_overlays = l.get_installed()

    for overlay in installed_overlays:
        logger.info('Cleaning cache for overlay %s...' % overlay)
        overlay_path = os.path.join(l.config['storage'], overlay)
        shutil.rmtree(os.path.join(overlay_path, 'metadata/cache'), True)
        shutil.rmtree(os.path.join(overlay_path, 'metadata/md5-cache'), True)

    # FIXME, try to find a way to log layman output...
    #l.sync(installed_overlays, output_results=False)
    cmd = ['layman', '-S', '--config', settings.LAYMAN_CONFIG]
    _launch_command(cmd, logger)

    cmd = ['egencache', '--jobs', "%s" % settings.EGENCACHE_JOBS,
           '--rsync', '--config-root', settings.PORTAGE_CONFIGROOT,
           '--update', '--update-use-local-desc']

    for overlay in installed_overlays:
        logger.info('Generating cache for overlay %s...' % overlay)
        overlay_path = os.path.join(l.config['storage'], overlay)
        repo_path = os.path.join(overlay_path, 'profiles/repo_name')
        if not os.path.exists(repo_path):
            continue
        _launch_command(cmd + ['--repo', overlay], logger)


def eix_update(logger):
    """
    Launches eix-update
    """
    cmd = ["eix-update"]
    return _launch_command(cmd, logger)


def update_portage_trees(logger=None):
    from djeuscan.processing import FakeLogger

    logger = logger or FakeLogger()
    logger.info("Running emerge --sync")
    emerge_sync(logger)
    logger.info("Running layman --sync")
    layman_sync(logger, cache=True)
    #logger.info("Running emerge --regen")
    #emerge_regen()
    logger.info("Running eix-update")
    eix_update(logger)
    logger.info("Done!")