param([string]$Location = 'eastus', [string]$VmSize = 'Standard_B2s')
$ErrorActionPreference = 'Stop'
$ProjectRoot = Split-Path $PSScriptRoot -Parent
$Azure = 'az'
if (Test-Path 'C:\Program Files\Microsoft SDKs\Azure\CLI2\wbin\az.cmd') { $Azure = 'C:\Program Files\Microsoft SDKs\Azure\CLI2\wbin\az.cmd' }
function Invoke-AzureJson([string[]]$Arguments) {
    $response = & $Azure @Arguments --output json --only-show-errors
    if ($LASTEXITCODE -ne 0) { throw "Azure CLI falhou: $($Arguments[0]) $($Arguments[1])" }
    if ($response) { return ($response -join "`n" | ConvertFrom-Json) }
}
$account = Invoke-AzureJson @('account','show')
if ($account.user.name -ne 'RM558710@fiap.com.br' -or $account.id -ne 'dda05624-99e8-4c3e-adad-af54a46e1811') { throw 'Entre com RM558710@fiap.com.br na assinatura Azure for Students autorizada.' }
$ResourceGroup = 'rg-zelacidade-orbital-rm558710'
$VmName = 'vm-orbital-rm558710'
$NsgName = 'nsg-orbital-rm558710'
$DnsLabel = 'zelacidade-orbital-rm558710-dda0'
$LocalDir = Join-Path $ProjectRoot '.local'
$KeyPath = Join-Path $LocalDir 'orbital_vm'
New-Item -ItemType Directory -Force $LocalDir | Out-Null
if (-not (Test-Path -LiteralPath $KeyPath)) {
    # O par gerado fica apenas na maquina local. Nunca incluir no ZIP.
    ssh-keygen -t ed25519 -f $KeyPath -N '""' -C 'orbital-rm558710'
    if ($LASTEXITCODE -ne 0) { throw 'Falha ao gerar chave SSH.' }
}
$ClientIp = (Invoke-RestMethod -Uri 'https://api.ipify.org').Trim()
if ($ClientIp -notmatch '^\d{1,3}(\.\d{1,3}){3}$') { throw 'IP publico IPv4 nao identificado.' }
Invoke-AzureJson @('provider','register','--namespace','Microsoft.Compute','--wait') | Out-Null
Invoke-AzureJson @('group','create','--name',$ResourceGroup,'--location',$Location,'--tags','projeto=ZelaCidadeOrbital','rm=558710','semestre=2026-1') | Out-Null
Invoke-AzureJson @('network','nsg','create','--resource-group',$ResourceGroup,'--name',$NsgName,'--location',$Location) | Out-Null
Invoke-AzureJson @('network','nsg','rule','create','-g',$ResourceGroup,'--nsg-name',$NsgName,'-n','SSH-Aluno','--priority','1000','--source-address-prefixes',"$ClientIp/32",'--destination-port-ranges','22','--protocol','Tcp','--access','Allow') | Out-Null
Invoke-AzureJson @('network','nsg','rule','create','-g',$ResourceGroup,'--nsg-name',$NsgName,'-n','API-Publica','--priority','1010','--source-address-prefixes','Internet','--destination-port-ranges','8080','--protocol','Tcp','--access','Allow') | Out-Null
$vms = @(Invoke-AzureJson @('vm','list','-g',$ResourceGroup))
if (-not ($vms | Where-Object { $_.name -eq $VmName })) {
    $CloudInit = Join-Path $LocalDir 'cloud-init.yml'
    $cloudText = @'
#cloud-config
package_update: true
packages:
  - docker.io
  - docker-compose-v2
  - git
  - curl
  - python3
  - openssl
runcmd:
  - systemctl enable --now docker
  - usermod -aG docker orbitaladmin
'@
    [IO.File]::WriteAllText($CloudInit, $cloudText, [Text.UTF8Encoding]::new($false))
    Invoke-AzureJson @('vm','create','-g',$ResourceGroup,'-n',$VmName,'--location',$Location,'--image','Ubuntu2404','--size',$VmSize,'--admin-username','orbitaladmin','--ssh-key-values',"$KeyPath.pub",'--authentication-type','ssh','--nsg',$NsgName,'--nsg-rule','NONE','--public-ip-address-dns-name',$DnsLabel,'--public-ip-sku','Standard','--storage-sku','StandardSSD_LRS','--os-disk-size-gb','32','--custom-data',$CloudInit) | Out-Null
}
$details = Invoke-AzureJson @('vm','show','-d','-g',$ResourceGroup,'-n',$VmName)
$evidenceDir = Join-Path $ProjectRoot 'evidencias'
New-Item -ItemType Directory -Force $evidenceDir | Out-Null
$SafeInfo = [ordered]@{ coletadoUtc = [DateTime]::UtcNow.ToString('o'); resourceGroup = $ResourceGroup; vm = $VmName; location = $Location; size = $VmSize; publicIp = $details.publicIps; dns = "$DnsLabel.$Location.cloudapp.azure.com"; swagger = "http://$DnsLabel.$Location.cloudapp.azure.com:8080/swagger"; status = $details.powerState; validacaoAplicacao = 'PENDENTE: executar validar-nuvem.py na VM' }
$SafeInfo | ConvertTo-Json | Set-Content -Encoding UTF8 (Join-Path $evidenceDir 'ambiente.json')
$SafeInfo | ConvertTo-Json
Write-Host "Conecte: ssh -i `"$KeyPath`" orbitaladmin@$($details.publicIps)"
