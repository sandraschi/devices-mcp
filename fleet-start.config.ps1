# Per-repo fleet start config for devices-mcp
# Edit ports/backend target here - start.ps1 is fleet-standard.
@{
    Name         = 'devices-mcp'
    BackendPort  = 10717
    FrontendPort = 10716
    HealthPath   = '/'
    WebRoot      = 'web-sota/frontend'
    NssmService  = 'devices-mcp'
    Backend = @{
        Kind = 'nssm'
    }
    Frontend = @{
        Kind           = 'vite-npm'
        PackageManager = 'npm'
        PortEnvVar     = 'VITE_PORT'
        ApiTargetEnv   = 'VITE_API_TARGET'
    }
}
