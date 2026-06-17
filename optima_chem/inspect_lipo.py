import deepchem as dc
import pandas as pd

tasks, data, transformers = dc.molnet.load_lipo(
    featurizer="ECFP",
    splitter="scaffold",
    transformers=["normalization"],
    reload=True,
)

# train, valid, test = datasets # UNNECESSARY for blackbox setup
dataset = data[0]

print("tasks:", tasks)
print("sizes:", len(dataset))
print("X:", dataset.X.shape)
print("y:", dataset.y.shape)
print("ids:", dataset.ids.shape)

y_raw = transformers[0].untransform(dataset.y)

for i in range(10):
    print({
        "i": i,
        "smiles": dataset.ids[i],
        "y_normalized": float(dataset.y[i][0]),
        "y_raw_logD": float(y_raw[i][0]),
    })

candidate_pool = pd.DataFrame({
    "candidate_id": range(len(dataset.ids)),
    "smiles": dataset.ids,
    "logD": y_raw[:, 0],
})

print(candidate_pool.head())
