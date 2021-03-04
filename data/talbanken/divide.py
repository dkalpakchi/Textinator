import json

if __name__ == '__main__':
    train = json.load(open('sv_talbanken-ud-train.json'))
    dev = json.load(open('sv_talbanken-ud-dev.json'))
    test = json.load(open('sv_talbanken-ud-test.json'))

    T, D, TT = len(train), len(dev), len(test)
    print(T, round(T / (T + D + TT), 4))
    print(D, round(D / (T + D + TT), 4))
    print(TT, round(TT / (T + D + TT), 4))