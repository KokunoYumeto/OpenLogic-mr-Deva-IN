param([int]$SlotTimeoutMilliseconds = 1500, [ValidateSet('sets','foundations','core')][string]$Target='sets')
$ErrorActionPreference = 'Stop'
$repoPath = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$buildPath = [IO.Path]::GetFullPath((Join-Path $repoPath ('build\'+$Target)))
$documentName = 'openlogic-mr-'+$Target
if (-not $buildPath.StartsWith($repoPath + [IO.Path]::DirectorySeparatorChar)) { throw 'Build path outside edition' }
$receiptPath = Join-Path $buildPath 'TEX_BUILD_RECEIPT.json'
$receiptHistory = Join-Path $buildPath ('TEX_BUILD_' + [DateTime]::UtcNow.ToString('yyyyMMddTHHmmssfff') + '.json')
$receipt = [ordered]@{schema='guarded-tex-build/1';mutex='Global\InterlanguageTeXSlotV1';acquired=$false;abandonedRecovery=$false;passes=@();result='not-started'}
Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
using System.Threading;
public static class EditionTexTree {
 [StructLayout(LayoutKind.Sequential,CharSet=CharSet.Unicode)] struct STARTUPINFO { public int cb; public string reserved; public string desktop; public string title; public int x,y,xs,ys,xc,yc,fill,flags; public short show,res2; public IntPtr reserved2,input,output,error; }
 [StructLayout(LayoutKind.Sequential)] struct PI { public IntPtr process,thread; public uint pid,tid; }
 [StructLayout(LayoutKind.Sequential)] struct BASIC { public long perProcess,perJob; public uint flags; public UIntPtr min,max; public uint active; public UIntPtr affinity; public uint priority,scheduling; }
 [StructLayout(LayoutKind.Sequential)] struct IO { public ulong ro,wo,oo,rt,wt,ot; }
 [StructLayout(LayoutKind.Sequential)] struct EXT { public BASIC basic; public IO io; public UIntPtr processMemory,jobMemory,peakProcess,peakJob; }
 [StructLayout(LayoutKind.Sequential)] struct ACCOUNT { public long user,kernel,periodUser,periodKernel; public uint faults,total,active,terminated; }
 [DllImport("kernel32.dll",CharSet=CharSet.Unicode,SetLastError=true)] static extern bool CreateProcess(string app,string cmd,IntPtr pa,IntPtr ta,bool inherit,uint flags,IntPtr env,string cwd,ref STARTUPINFO si,out PI pi);
 [DllImport("kernel32.dll",CharSet=CharSet.Unicode)] static extern IntPtr CreateJobObject(IntPtr a,string name);
 [DllImport("kernel32.dll")] static extern bool SetInformationJobObject(IntPtr job,int c,ref EXT info,int size);
 [DllImport("kernel32.dll")] static extern bool AssignProcessToJobObject(IntPtr j,IntPtr p);
 [DllImport("kernel32.dll")] static extern uint ResumeThread(IntPtr h);
 [DllImport("kernel32.dll")] static extern bool QueryInformationJobObject(IntPtr j,int c,out ACCOUNT info,int size,IntPtr n);
 [DllImport("kernel32.dll")] static extern bool GetExitCodeProcess(IntPtr h,out uint c);
 [DllImport("kernel32.dll")] static extern bool TerminateProcess(IntPtr h,uint c);
 [DllImport("kernel32.dll")] static extern bool TerminateJobObject(IntPtr h,uint c);
 [DllImport("kernel32.dll")] static extern bool CloseHandle(IntPtr h);
 public static int Run(string app,string args,string cwd,int timeout) {
  IntPtr job=CreateJobObject(IntPtr.Zero,null); if(job==IntPtr.Zero)throw new Exception("CreateJobObject failed");
  EXT limit=new EXT();limit.basic.flags=0x2000;
  PI pi=new PI();bool created=false,assigned=false;
  try {
   if(!SetInformationJobObject(job,9,ref limit,Marshal.SizeOf(typeof(EXT))))throw new Exception("Job limit setup failed");
   STARTUPINFO si=new STARTUPINFO();si.cb=Marshal.SizeOf(typeof(STARTUPINFO));si.flags=1;si.show=0;
   if(!CreateProcess(app,"\""+app+"\" "+args,IntPtr.Zero,IntPtr.Zero,false,0x08000004,IntPtr.Zero,cwd,ref si,out pi))throw new Exception("CreateProcess failed "+Marshal.GetLastWin32Error());
   created=true;
   if(!AssignProcessToJobObject(job,pi.process)){TerminateProcess(pi.process,97);throw new Exception("Cannot capture owned process tree; failed closed");}
   assigned=true;if(ResumeThread(pi.thread)==0xffffffff)throw new Exception("Resume failed");
   var until=DateTime.UtcNow.AddMilliseconds(timeout);
   while(true){ACCOUNT a;if(!QueryInformationJobObject(job,1,out a,Marshal.SizeOf(typeof(ACCOUNT)),IntPtr.Zero))throw new Exception("Job accounting failed");if(a.active==0)break;if(DateTime.UtcNow>until){TerminateJobObject(job,98);throw new Exception("Owned TeX tree exceeded bounded runtime");}Thread.Sleep(150);}
   uint code;if(!GetExitCodeProcess(pi.process,out code))throw new Exception("Exit status unavailable");return (int)code;
  } finally {
   if(assigned){ACCOUNT a;if(QueryInformationJobObject(job,1,out a,Marshal.SizeOf(typeof(ACCOUNT)),IntPtr.Zero)&&a.active>0){TerminateJobObject(job,99);do {Thread.Sleep(50);if(!QueryInformationJobObject(job,1,out a,Marshal.SizeOf(typeof(ACCOUNT)),IntPtr.Zero))break;}while(a.active>0);}}
   else if(created)TerminateProcess(pi.process,99);
   if(pi.thread!=IntPtr.Zero)CloseHandle(pi.thread);if(pi.process!=IntPtr.Zero)CloseHandle(pi.process);CloseHandle(job);
  }
 }
}
'@
$mutex = [Threading.Mutex]::new($false, 'Global\InterlanguageTeXSlotV1')
$held = $false
$previousSourceDateEpoch = $env:SOURCE_DATE_EPOCH
try {
  try { $held = $mutex.WaitOne($SlotTimeoutMilliseconds) } catch [Threading.AbandonedMutexException] { $held=$true; $receipt.abandonedRecovery=$true }
  if (-not $held) { $receipt.result='slot-occupied'; return }
  $receipt.acquired=$true
  $receipt['texInputSha256']=(Get-FileHash -LiteralPath (Join-Path $buildPath ($documentName+'.tex')) -Algorithm SHA256).Hash.ToLower()
  $env:SOURCE_DATE_EPOCH='1788480000'
  $receipt['sourceDateEpoch']='1788480000'
  $engine = (Get-Command xelatex.exe -ErrorAction Stop).Source
  for ($pass=1; $pass -le 2; $pass++) {
    $code=[EditionTexTree]::Run($engine,('-no-shell-escape -interaction=nonstopmode -halt-on-error -file-line-error '+$documentName+'.tex'),$buildPath,240000)
    $logPath=Join-Path $buildPath ($documentName+'.log')
    $log=if(Test-Path -LiteralPath $logPath){Get-Content -LiteralPath $logPath -Raw}else{''}
    $receipt.passes+=@{pass=$pass;exitCode=$code;logSha256=if($log){(Get-FileHash -LiteralPath $logPath -Algorithm SHA256).Hash.ToLower()}else{$null}}
    if ($code -ne 0) { $receipt.result='tex-failed'; Write-Output (($log -split "`n" | Select-Object -Last 24) -join "`n"); return }
  }
  $warnings=@($log -split "`n" | Where-Object { $_ -match 'Missing character|Overfull|undefined references|Undefined control sequence|LaTeX Error' })
  $receipt['warnings']=$warnings
  $pdf=Join-Path $buildPath ($documentName+'.pdf')
  $receipt['pdf']=@{name=($documentName+'.pdf');bytes=(Get-Item -LiteralPath $pdf).Length;sha256=(Get-FileHash -LiteralPath $pdf -Algorithm SHA256).Hash.ToLower()}
  $receipt.result=if($warnings.Count){'built-with-defects'}else{'built-log-clean'}
} finally {
  $receipt | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $receiptPath -Encoding utf8
  Copy-Item -LiteralPath $receiptPath -Destination $receiptHistory
  if($receipt.result -eq 'built-log-clean') { Copy-Item -LiteralPath $receiptPath -Destination (Join-Path $buildPath 'TEX_SUCCESS_RECEIPT.json') }
  if($held){$mutex.ReleaseMutex()};$mutex.Dispose()
  $env:SOURCE_DATE_EPOCH=$previousSourceDateEpoch
  Write-Output ($receipt | ConvertTo-Json -Depth 8)
}
