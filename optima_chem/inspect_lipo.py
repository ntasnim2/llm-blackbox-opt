import deepchem as dc

tasks, datasets, transformers = dc.molnet.load_lipo(
    featurizer="ECFP",
    splitter="scaffold",
    transformers=["normalization"],
    reload=True,
)

train, valid, test = datasets

print("tasks:", tasks)
print("sizes:", len(train), len(valid), len(test))
print("X:", train.X.shape)
print("y:", train.y.shape)
print("ids:", train.ids.shape)

y_raw = transformers[0].untransform(train.y)

for i in range(10):
    print({
        "i": i,
        "smiles": train.ids[i],
        "y_normalized": float(train.y[i][0]),
        "y_raw_logD": float(y_raw[i][0]),
    })
