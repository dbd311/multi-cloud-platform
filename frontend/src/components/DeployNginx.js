import React, { useState } from 'react';
import axios from 'axios';
import CloudProviderSelect from './CloudProviderSelect';
import DomainInput from './DomainInput';
import DeploymentStatus from './DeploymentStatus';

function DeployNginx() {
  const [publicUrl, setPublicUrl] = useState('');
  const [cloudProvider, setCloudProvider] = useState('gcp'); // Default cloud provider
  const [domain, setDomain] = useState('');
  const [error, setError] = useState('');
  const [isLoggedIn, setIsLoggedIn] = useState(false); // Track login status
  const [userRole, setUserRole] = useState(''); // Track user role (developer or admin)
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');

  // Regex to validate domain names
  const domainRegex = /^(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,}$/i;

  // Handle login
  const handleLogin = async () => {
    try {
      const response = await axios.post('http://localhost:5000/login', {
        username,
        password,
      });

      if (response.data.success) {
        setIsLoggedIn(true);
        setUserRole(response.data.role); // Set user role from the backend
        setError('');
      } else {
        setError('Invalid username or password.');
      }
    } catch (err) {
      setError('Failed to login. Please try again.');
    }
  };

  // Handle logout
  const handleLogout = () => {
    setIsLoggedIn(false);
    setUserRole('');
    setUsername('');
    setPassword('');
  };

  // Handle deployment (for developers)
  const handleDeploy = async () => {
    if (!domainRegex.test(domain)) {
      setError('Please enter a valid domain name, e.g. example.com example123.ch etc.');
      return;
    }

    setError(''); // Clear any previous errors

    try {
      const response = await axios.post('http://localhost:5000/deploy', {
        cloud_provider: cloudProvider,
        domain: domain,
      });
      setPublicUrl(response.data.public_url);
    } catch (err) {
      setError('Failed to deploy Nginx. Please try again.');
    }
  };

  // Render login form if not logged in
  if (!isLoggedIn) {
    return (
      <div>
        <h1>Nginx Deployment Platform (multi-cloud, multi-tenant)</h1>
        <div>
          <label htmlFor="username">Username: </label>
          <input
            type="text"
            id="username"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            placeholder="Enter your username"
          />
        </div>
        <div>
          <label htmlFor="password">Password: </label>
          <input
            type="password"
            id="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="Enter your password"
          />
        </div>
        <button onClick={handleLogin}>Login</button>
        {error && <p style={{ color: 'red' }}>{error}</p>}
      </div>
    );
  }

  // Render deployment form for developers
  if (userRole === 'developer') {
    return (
      <div>
        <h1>Nginx Deployment Platform (multi-cloud, multi-tenant)</h1>
        <button onClick={handleLogout} style={{ float: 'right' }}>Logout</button>
        <CloudProviderSelect
          cloudProvider={cloudProvider}
          setCloudProvider={setCloudProvider}
        />
        <Settings
          value={domain}
          onChange={setDomain}
          error={error}
          setError={setError}
        />
        <button onClick={handleDeploy}>Deploy Nginx</button>
        <DeploymentStatus publicUrl={publicUrl} />
      </div>
    );
  }

  // Render admin form for admins
  if (userRole === 'admin') {
    return (
      <div>
        <h1>Admin Dashboard</h1>
        <button onClick={handleLogout} style={{ float: 'right' }}>Logout</button>
        <p>Welcome, Admin! Here you can manage users, monitor deployments, and more.</p>
        {/* Admin dashboard is under construction ... */}
      </div>
    );
  }

  // Default fallback (e.g., if role is unknown)
  return (
    <div>
      <h1>Welcome!</h1>
      <p>Your role does not have access to any specific features.</p>
      <button onClick={handleLogout}>Logout</button>
    </div>
  );
}

export default DeployNginx;