"""Small deterministic PCA view of real embeddings; raw vectors stay private."""
import numpy as np

def cluster_vectors(rows,max_clusters=10,iterations=24):
    """Deterministic spherical k-means over normalized embeddings."""
    valid=[]
    for row in rows:
        if row['vector'] is None:continue
        value=np.asarray(row['vector'],dtype=float)
        if value.ndim==1 and np.isfinite(value).all() and np.linalg.norm(value)>0:valid.append((str(row['id']),value/np.linalg.norm(value)))
    if not valid:return {},{},{}
    matrix=np.stack([value for _,value in valid]);count=len(valid);k=max(1,min(max_clusters,int(np.ceil(np.sqrt(count)))))
    chosen=[int(np.argmax(matrix@matrix.mean(axis=0)))]
    while len(chosen)<k:
        nearest=np.max(matrix@matrix[chosen].T,axis=1);nearest[chosen]=1;chosen.append(int(np.argmin(nearest)))
    centroids=matrix[chosen].copy();labels=np.zeros(count,dtype=int)
    for step in range(iterations):
        updated=np.argmax(matrix@centroids.T,axis=1)
        if np.array_equal(updated,labels) and step>0:break
        labels=updated
        for index in range(k):
            members=matrix[labels==index]
            if len(members):
                centroid=members.mean(axis=0);norm=np.linalg.norm(centroid)
                if norm:centroids[index]=centroid/norm
    sizes={index:int(np.sum(labels==index)) for index in range(k)}
    ordered=sorted(range(k),key=lambda index:(-sizes[index],min(i for i,x in enumerate(labels) if x==index)))
    display={raw:index+1 for index,raw in enumerate(ordered)}
    return ({key:display[int(labels[i])] for i,(key,_) in enumerate(valid)},
            {key:sizes[int(labels[i])] for i,(key,_) in enumerate(valid)},
            {key:float(matrix[i]@centroids[int(labels[i])]) for i,(key,_) in enumerate(valid)})

def project_vectors(rows):
    valid=[]
    for row in rows:
        if row['vector'] is None:continue
        value=np.asarray(row['vector'],dtype=float)
        if value.ndim==1 and np.isfinite(value).all() and np.linalg.norm(value)>0:
            valid.append((str(row['id']),value/np.linalg.norm(value)))
    if not valid:return {},0.0
    matrix=np.stack([v for _,v in valid]);matrix-=matrix.mean(axis=0)
    u,s,v=np.linalg.svd(matrix,full_matrices=False)
    count=min(3,len(s));coords=u[:,:count]*s[:count]
    for axis in range(count):
        if v[axis,np.argmax(np.abs(v[axis]))]<0:coords[:,axis]*=-1
    coords=np.pad(coords,((0,0),(0,3-count)))
    scale=float(np.max(np.linalg.norm(coords,axis=1))) or 1
    variance=float(np.sum(s[:count]**2)/np.sum(s**2)) if np.sum(s**2)>0 else 0.0
    return {key:coords[i].tolist() for i,(key,_) in enumerate(valid)} if scale==1 else {key:(coords[i]/scale).tolist() for i,(key,_) in enumerate(valid)},variance
