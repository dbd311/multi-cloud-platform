import React from 'react';

function DeploymentStatus({ publicUrl }) {
  if (!publicUrl) {
    return null; // Don't render anything if there's no public URL
  }

  return (
    <div>
      <h2>Deployment Successful!</h2>
      <p>
        Access your Nginx instance at:{' '}
        <a href={publicUrl} target="_blank" rel="noopener noreferrer">
          {publicUrl}
        </a>
      </p>
    </div>
  );
}

export default DeploymentStatus;