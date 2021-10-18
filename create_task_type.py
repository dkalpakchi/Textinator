import os
import argparse
import yaml


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('spec', type=str, default='YAML specification file')
    args = parser.parse_args()

    spec = yaml.load(open(args.spec))

    if not os.path.exists(spec['type']):
        os.mkdir(spec['type'])

    with open(os.path.join(spec['type'], '__init__.py'), 'w') as f:
        pass

    with open(os.path.join(spec['type'], 'datasource.py'), 'w') as f:
        f.write("# This is a generated file\n\n")

    with open(os.path.join(spec['type'], 'display.html'), 'w') as f:
        f.write("<!-- This is a generated file -->\n\n")



