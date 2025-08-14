# Gnosis Auth Deployment Script
# Target: local, staging, production, cloudrun
# Options: -Rebuild, -Logs, -WhatIf, -Help

param(
    [string]$Target = "local",
    [string]$Tag = "latest",
    [switch]$Rebuild,
    [switch]$SkipBuild,
    [switch]$Logs,
    [switch]$WhatIf,
    [switch]$Help
)

# --- Help ---
if ($Help) {
    Write-Host @"
Gnosis Auth Deployment Script

Usage:
./deploy.ps1 [options]

Parameters:
-Target      Deployment target (local, staging, production, cloudrun). Default: local
-Tag         Docker image tag. Default: latest
-Rebuild     Force rebuild with --no-cache
-SkipBuild   Skip Docker build step
-Logs        Show logs after deployment (local only)
-WhatIf      Preview deployment without executing
-Help        Show this help message
"@
    exit 0
}

# --- Functions ---
function Write-Log {
    param([string]$Message, [string]$Color = "White")
    Write-Host "[$([datetime]::now.ToString('HH:mm:ss'))] $Message" -ForegroundColor $Color
}

function Run-Command {
    param([string]$Command, [switch]$NoWhatIf)
    Write-Log "Running: $Command" -Color "Cyan"
    if (-not $WhatIf -or $NoWhatIf) {
        Invoke-Expression $Command
        if ($LASTEXITCODE -ne 0) {
            Write-Log "Command failed!" -Color "Red"
            exit 1
        }
    }
}

# --- Main ---
Write-Log "Starting deployment for target: $Target" -Color "Green"

# --- Local Deployment ---
if ($Target -eq "local") {
    if (-not $SkipBuild) {
        $BuildCommand = "docker-compose build"
        if ($Rebuild) {
            $BuildCommand += " --no-cache"
        }
        Run-Command $BuildCommand
    }

    Run-Command "docker-compose up -d"

    if ($Logs) {
        Run-Command "docker-compose logs -f auth"
    }
    Write-Log "Local deployment complete." -Color "Green"
    Write-Log "Access at http://localhost:5000"
    exit 0
}

# --- Cloud Run Deployment ---
if ($Target -in @("staging", "production", "cloudrun")) {
    $EnvFile = ".env.$Target"
    if (-not (Test-Path $EnvFile)) {
        Write-Log "Environment file '$EnvFile' not found for target '$Target'." -Color "Red"
        exit 1
    }

    # Load environment variables from the specified file
    $envConfig = @{}
    Get-Content $EnvFile | Where-Object { $_ -match '^\s*[^#].*=' } | ForEach-Object {
        $key, $value = $_ -split '=', 2
        $trimmedValue = $value.Trim()
        if (($trimmedValue.StartsWith('"') -and $trimmedValue.EndsWith('"')) -or ($trimmedValue.StartsWith("'") -and $trimmedValue.EndsWith("'"))) {
            $trimmedValue = $trimmedValue.Substring(1, $trimmedValue.Length - 2)
        }
        $envConfig[$key.Trim()] = $trimmedValue
    }

                $GcpServiceAccount = $envConfig["GCP_SERVICE_ACCOUNT"]
    $GcsBucketName = $envConfig["GCS_BUCKET_NAME"]
    $ServiceName = "gnosis-auth" # Use a fixed service name
    $ImageUrl = "${GcpRegion}-docker.pkg.dev/${ProjectId}/${ArtifactRegistry}/${ServiceName}:${Tag}"

    # --- Pre-flight Checks ---
    Write-Log "Performing pre-flight checks..."
    if ($GcsBucketName) {
        Write-Log "Ensuring GCS Bucket 'gs://$GcsBucketName' exists..."
        $bucketExists = gcloud storage buckets list --project=$ProjectId --filter="name=$GcsBucketName" --format="value(name)"
        if (-not $bucketExists) {
            Write-Log "Bucket not found. Creating GCS bucket 'gs://$GcsBucketName' in region '$GcpRegion'..." -Color "Yellow"
            gcloud storage buckets create "gs://$GcsBucketName" --project=$ProjectId --location=$GcpRegion --uniform-bucket-level-access
            Write-Log "✓ Bucket created successfully." -Color "Green"
        } else {
            Write-Log "✓ Bucket already exists." -Color "Green"
        }
    } else {
        Write-Log "GCS_BUCKET_NAME not set, skipping bucket check." -Color "Yellow"
    }
    # --- End Pre-flight Checks ---

    if (-not $SkipBuild) {
        Run-Command "docker build -t $ImageUrl ."
        Run-Command "docker push $ImageUrl"
    }

    # --- Deploy to Cloud Run ---
    Write-Log "Deploying service '$ServiceName' to Cloud Run..." -Color "White"
    
    # Create a temporary YAML file for environment variables
    $envYamlFile = "temp_env.yaml"
    $yamlContent = ""
    $envConfig.GetEnumerator() | ForEach-Object {
        $yamlContent += "$($_.Key): `"$($_.Value)`"`n"
    }
    Set-Content -Path $envYamlFile -Value $yamlContent

    $deployArgs = @(
        "run", "deploy", $ServiceName,
        "--image", $ImageUrl,
        "--region", $GcpRegion,
        "--platform", "managed",
        "--allow-unauthenticated",
        "--service-account", $GcpServiceAccount,
        "--port", "5000",
        "--env-vars-file", $envYamlFile
    )
    
    try {
        if (-not $WhatIf) {
            & gcloud @deployArgs
            if ($LASTEXITCODE -eq 0) {
                $serviceUrl = & gcloud run services describe $ServiceName --region=$GcpRegion --format="value(status.url)"
                Write-Log "✓ CLOUD RUN DEPLOYMENT SUCCESSFUL!" -ForegroundColor "Green"
                Write-Log "🔗 Service URL: $serviceUrl" -ForegroundColor "Cyan"
            } else {
                Write-Error "Cloud Run deployment failed."
            }
        } else {
            Write-Log "WhatIf: gcloud $($deployArgs -join ' ')" -Color "Yellow"
        }
    } finally {
        # Clean up the temporary file
        if (Test-Path $envYamlFile) {
            Remove-Item $envYamlFile -ErrorAction SilentlyContinue
        }
    }
    exit 0
}

Write-Log "Invalid target: $Target" -Color "Red"
exit 1
