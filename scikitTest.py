from sklearn import datasets
from sklearn.linear_model import LinearRegression
import matplotlib.pyplot as plt

boston = datasets.load_boston()
x = boston.data
y = boston.target
model = LinearRegression()
model.fit(x, y)
print model.predict(x[:4, :])
print y[:4]

x, y = datasets.make_regression(n_samples=100, n_features=1, n_targets=1, noise=10)
plt.scatter(x, y)
plt.show()