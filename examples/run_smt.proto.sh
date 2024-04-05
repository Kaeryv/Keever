set -e
python examples/smt_sbo.py {{method}} {{db:npz.all}}
touch {{touchfile}}
