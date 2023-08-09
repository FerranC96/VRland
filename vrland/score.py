# AUTOGENERATED! DO NOT EDIT! File to edit: ../nbs/00_score.ipynb.

# %% auto 0
__all__ = ['foo', 'check_inversevvl', 'scale_metrics', 'compute_distdeg', 'bycluster_median', 'compute_vr_scores']

# %% ../nbs/00_score.ipynb 4
def foo(): pass

# %% ../nbs/00_score.ipynb 12
def check_inversevvl(dataframe, param_dict):

    if param_dict["dynamic"] == "velocity_length":
        print("Computing the inverse of the RNA velocity values")
        cell_data["inverse_vvl"] = 1/cell_data[param_dict["dynamic"]]
        param_dict["dynamic"] = "inverse_vvl"
    
    return dataframe, param_dict

# %% ../nbs/00_score.ipynb 14
def scale_metrics(dataframe, metrics = ["CCAT","inverse_vvl"]):
    
    from sklearn.preprocessing import MinMaxScaler
    
    for i in metrics:
        dataframe[i] = MinMaxScaler().fit_transform(X = dataframe[[i]])
    
    return dataframe

# %% ../nbs/00_score.ipynb 19
def compute_distdeg(input_df, dim_name = ["phate1","phate2"], split_by="curatedCLUST", 
    knn=30, distance_mode = "centroid", distance_metric = "manhattan", scale = True, inv_degree=True,
    plot=False, rmv_outliers=False):
    """
    Computes distances and degrees of cells within a cluster.
    Results will get scaled within the cluster level so it handles them as independent entities.
    
    Parameters
    ----------
    G
        NetworkX graph
        
    Returns
    -------
    properties : str
        Concatenated string with number of edges and of nodes, the average degree and the graph's density
    """
    import pandas as pd, graphtools, numpy as np

    output_df = pd.DataFrame(columns=dim_name+["dist","deg"])
    for i in input_df[split_by].unique():
        df_dist = input_df.loc[input_df[split_by]==i,dim_name]
        #Knn param is key and must be tunned according to the size of the cluster
        G = graphtools.Graph(df_dist.values, knn=knn, decay=None, distance=distance_metric)
        df_dist["deg"] = G.to_pygsp().d
        
        if distance_mode == "alphashape":
            #Find alphashape vertices. Compute min distance of cell to vertices
            print(f"Computing shape-based distance for cluster {i}")
            print("WARNING: This is not implemented yet, using centroids instead")
            distance_mode = "centroid"
        if distance_mode == "centroid":
            # Return distances by using shortest_path
            print(f"Computing centroid distance for cluster {i}")
            np_dist = G.shortest_path(distance="data")
            #Compute median distance to all cells for al cells -> min should be a centroid
            df_dist["dist"] = np.median(np_dist, axis=1)
            
        #With low knn values sometimes cells become isolated. Substitute those infinite distances by max finite value
        if np.any(np.isinf(df_dist["dist"])):
            max_finite = np.max(df_dist["dist"][np.isfinite(df_dist["dist"])])
            df_dist["dist"].replace([np.inf], max_finite, inplace=True)

        if rmv_outliers:
            #Replace distant outliers with median value -> DONE to smoothen landscape at the very edges of a cluster
            df_dist["dist"] = np.where(
                                df_dist["dist"]>np.percentile(df_dist["dist"],99), 
                                df_dist["dist"].median(), 
                                df_dist["dist"])
        if scale:
            from sklearn.preprocessing import MinMaxScaler
            df_dist["dist_scaled"] = MinMaxScaler().fit_transform(X = df_dist[["dist"]])
            df_dist["inv_deg_scaled"] = MinMaxScaler().fit_transform(X = 1/df_dist[["deg"]])
        if plot:
            import matplotlib.pyplot as plt
            #Plot cluster cells on phate and colour by distance from centroid
            plt.scatter(df_dist[dim_name[0]],df_dist[dim_name[1]],c=df_dist["dist"])
            plt.show()
            # plt.scatter(df_dist[dim_name[0]],df_dist[dim_name[1]],c=df_dist["deg"])
            # plt.show()

        output_df = pd.concat([output_df, df_dist])

    return output_df



# %% ../nbs/00_score.ipynb 20
def bycluster_median(dataframe, param_dict):

    dataframe["potency_med"] = dataframe.groupby(by=param_dict["cluster"]
                                )[[param_dict["potency"]]].transform("median")
    dataframe["dynamic_med"] = dataframe.groupby(by=param_dict["cluster"]
                                )[[param_dict["dynamic"]]].transform("median")

    return dataframe

# %% ../nbs/00_score.ipynb 21
def compute_vr_scores(dataframe, param_dict, global_dist = False):

    cond_dfs = []

    if global_dist == True:
        dist_df = compute_distdeg(dataframe, dim_name = param_dict["dim_names"], 
            split_by=param_dict["cluster"], distance_mode = "alphashape", 
            knn=5, plot=False, rmv_outliers=False)
        dataframe = pd.merge(dataframe, dist_df.sort_index(), how="left", on=param_dict["dim_names"])

    for s in dataframe[param_dict["condition"]].unique():
        print (s)
        condition_data = dataframe.loc[dataframe[param_dict["condition"]]==s]
        
        if global_dist == False:
            dist_df = compute_distdeg(condition_data, dim_name = param_dict["dim_names"], 
                split_by=param_dict["cluster"], distance_mode = "alphashape", 
                knn=5, plot=False, rmv_outliers=False)
            condition_data = pd.merge(condition_data, dist_df.sort_index(), how="left", on=param_dict["dim_names"])

        condition_data = bycluster_median(condition_data, param_dict)
        
        condition_data["VR"] = condition_data.apply(
        lambda x: 0.9*x["potency_med"]+0.1*(x["dynamic_med"]*x["dist_scaled"]),
        axis=1)
        print(condition_data.columns)
        cond_dfs.append(condition_data)
    
    out_df = pd.concat(cond_dfs)

    return out_df

