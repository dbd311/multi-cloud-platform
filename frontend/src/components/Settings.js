import React, { useState } from 'react';

function Settings({ value, onChange, error, setError }) {
  // Regex to validate domain names
  const domainRegex = /^(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,}$/i;

  const handleChange = (e) => {
    const inputValue = e.target.value;
    onChange(inputValue); // Pass the value to the parent component

    // Validate the domain in real-time
    if (!domainRegex.test(inputValue)) {
      setError('Please enter a valid domain name.');
    } else {
      setError('');
    }
  };

  return (
    <div>
      <label htmlFor="domain">Domain: </label>
      <input
        type="text"
        id="domain"
        value={value}
        onChange={handleChange}
        placeholder="Enter a valid domain (e.g., example.com)"
        style={{ border: error ? '1px solid red' : '1px solid #ccc' }}
      />
      {error && <p style={{ color: 'red', fontSize: '0.875rem', marginTop: '0.25rem' }}>{error}</p>}
    </div>
	<div>
      <label htmlFor="namespace">Namespace: </label>
      <input
        type="text"
        id="namespace"
        value={value}        
        placeholder="Enter a valid namespace e.g. awscloud"
        style={{ border: error ? '1px solid red' : '1px solid #ccc' }}
      />
    </div>
	<div>
      <label htmlFor="appname">App name: </label>
      <input
        type="text"
        id="appname"
        value={value}        
        placeholder="Enter a valid app name, e.g. nginx-12345"
        style={{ border: error ? '1px solid red' : '1px solid #ccc' }}
      />
    </div>
  );
}

export default Settings;