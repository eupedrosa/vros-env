
import os
import sys
import yaml

from .env import ROSVenv, EnvNotFound, EnvAlreadyExist

name = 'init'
desc = 'Initialize the current directory with a ROS virtual environment.'

def prepare_arguments(parser):
    parser.add_argument('--distro', type=str,
            default=os.environ.get('ROS_DISTRO', default='melodic'),
            help='ROS distro')
    parser.add_argument('-b', '--build', action='store_true', default=False,
            help='build user base image if it does not exist')
    parser.add_argument('--all', action='store_true', default=False,
            help='add all directories to the mount list')
    parser.add_argument('--dir', type=str, action='append',
            help='add DIR to mount the mount list')
    parser.add_argument('--overlay', action='store_true', default=False,
            help='create an overlay environment from `overlay.yml`')

    return parser


def run(args):
    try:
        return _init(args)
    except EnvAlreadyExist as e:
        print(e)
    except FileNotFoundError as e:
        print(e)
    return 1


def _init(args):

    cwd = os.getcwd()
    env = ROSVenv()

    # Possible mounts
    mounts = [x for x in os.listdir(cwd)]
    if not args.all:
        # The argument --all was not used.
        # Hence, only the directories added with --dir will go to the mount list.
        mounts = list(set(args.dir or []))

    print(mounts)
    mounts = { os.path.basename(cwd): mounts }

    # Add extra mounts if this is an overlay
    if args.overlay:
        print('overlay')
        with open('overlay.yml') as f:
            overlay = yaml.load(f, Loader=yaml.SafeLoader)

        for p in overlay['overlays']:
            overlay_path = os.path.abspath(os.path.expanduser(p))
            sigfile = os.path.join(overlay_path, 'ROSvenv')
            if not os.path.isfile(sigfile):
                print(f"The path '{overlay_path}' is not an ROS environment")
                exit(1)

            with open(sigfile, 'r') as f:
                overlay_info = yaml.load(f, Loader=yaml.SafeLoader)
            for k, v in overlay_info['mounts'].items():
                mounts[k] = []
                for p in v:
                    if os.path.isabs(p):
                        mounts[k].append(p)
                    else:
                        mounts[k].append(os.path.join(overlay_path, p))

    env.signify(cwd, args.distro, mounts)
    env.attach(cwd)

    env.print()

    if not env.env_base_exists:
        build = args.build

        if not build:
            print('Base user image does not exist, build it now? [y/N]', end=' ')
            choice = input().lower()
            if choice and choice[0] == 'y':
                build = True

        if build:
            print(f'Building base, please wait...', end=' ', flush=True)
            ok = env.build_base()
            if ok:
                print('[DONE]')
            else:
                print('[FAIL]')

        else:
            print('WARNING: user base image not built, use `vre run` to trigger a build.')

    return 0

