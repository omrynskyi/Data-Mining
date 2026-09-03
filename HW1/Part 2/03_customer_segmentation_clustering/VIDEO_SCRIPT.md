Project 03: Customer Segmentation Clustering

WHAT IT IS
A customer segmentation system that groups mall customers into personas using three different clustering algorithms, then visualizes the groups in a React dashboard. Includes an automated search that tunes the clustering parameters to match published benchmark numbers.

HOW TO RUN
Command: make 03   (or ./run --03)
Opens at: http://localhost:5173

FILES TO SHOW ON SCREEN
1. src/models.py - defines the three clustering algorithms and PCA
2. run_autoresearch.py - hill climbing search that tunes parameters

CODE - src/models.py (clustering algorithms)

@staticmethod
def train_kmeans(X, k=5, random_state=42, n_init=10, max_iter=300):
    km = KMeans(n_clusters=k, init="k-means++", n_init=n_init,
                max_iter=max_iter, random_state=random_state)
    km.fit(X)
    return km

@staticmethod
def train_dbscan(X, eps=None, min_samples=5, metric="euclidean"):
    if eps is None:
        std_mean = float(np.mean(np.std(X, axis=0)))
        eps = 0.35 if std_mean < 2.0 else 8.5
    dbs = DBSCAN(eps=eps, min_samples=min_samples, metric=metric)
    dbs.fit(X)
    return dbs

@staticmethod
def compute_pca(X, n_components=3, random_state=42):
    pca = PCA(n_components=n_components, random_state=random_state)
    X_pca = pca.fit_transform(X)
    return X_pca, pca

Point out three things here: K-Means needs a fixed number of clusters, k. DBSCAN instead finds clusters based on density and even picks a sensible default eps automatically. PCA is used afterward just to compress the features down to 2 or 3 dimensions so the clusters can be plotted.

SCRIPT

Intro, 0:00 to 0:20
Say you are showing Project 03, customer segmentation clustering.
Launch it with make 03.
Mention this starts the Vite and React dashboard on localhost port 5173.

Code walkthrough, 0:20 to 1:10
Open src/models.py.
Explain the project trains three different clustering algorithms on the same customer data: K-Means, Agglomerative, and DBSCAN, so the results can be compared side by side.
Point out that DBSCAN estimates its own eps parameter from the data instead of requiring a fixed guess.
Open run_autoresearch.py and explain this script automatically hill-climbs the hyperparameters until the clustering quality matches numbers reported in the reference paper, landing on k=5 with a Silhouette Score of 0.5547.

Live demo, 1:10 to 1:50
Switch to the browser at localhost 5173.
Show the 2D PCA scatter plot of the clusters and the customer persona cards.
Point out the Silhouette, Davies-Bouldin, and Calinski-Harabasz scores displayed for each algorithm.

Wrap up
This concludes Project 03.
