import React from 'react';

function CloudProviderSelect({ cloudProvider, setCloudProvider }) {
  return (
    <div>
      <label>Select Cloud Provider:</label>
      <select
        value={cloudProvider}
        onChange={(e) => setCloudProvider(e.target.value)}
      >
        <option value="aws">AWS (EKS)</option>
        <option value="gcp">GCP (GKE)</option>
        <option value="azure">Azure (AKS)</option>
      </select>
    </div>
  );
}