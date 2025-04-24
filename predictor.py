import numpy as np
from sklearn.neighbors import KNeighborsRegressor

def predict_split(activity, group_type, num_people):
    context_features = {
        'dining': 0, 'travel': 1, 'shopping': 2,
        'friends': 0, 'family': 1, 'colleagues': 2
    }
    X_train = np.array([[0, 0, 3], [1, 1, 4], [2, 2, 2]])  # dummy data
    y_train = np.array([[0.33, 0.33, 0.34], [0.25]*4, [0.6, 0.4]])

    model = KNeighborsRegressor(n_neighbors=1)
    model.fit(X_train, y_train)

    x_input = np.array([[context_features[activity], context_features[group_type], num_people]])
    pred = model.predict(x_input)
    return pred[0].tolist()
