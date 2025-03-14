
src/
├── components/
│   ├── DeployNginx.js       # Main deployment component
│   ├── CloudProviderSelect.js # Dropdown for cloud provider selection
│   └── DeploymentStatus.js   # Component to display deployment status
    ....and Other components
├── App.js                   # Main application component
├── index.js                 # Entry point
└── styles/
    └── App.css              # Styles for the application
	
	
Description of the components:
	
  CloudProviderSelect.js: Renders a dropdown for selecting the cloud provider.

  DeploymentStatus.js: Displays the public URL of the deployed Nginx instance.

  DeployNginx.js: Combines the above components and handles the deployment logic.


Main component:
  App.js: Renders the DeployNginx component.

index.js: Entry point of the application.

When compile the frontend using npm run build, React will generate the following structure:

#build/
#    ├── index.html
#    ├── static/
#    │   ├── js/
#    │   │   └── main.[hash].js
#    │   ├── css/
#    │   │   └── main.[hash].css
#    └── assets/
#

# then we need to copy the build folder to nginx share folder
COPY --from=build /app/build /usr/share/nginx/html


