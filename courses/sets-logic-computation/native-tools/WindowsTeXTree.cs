using System;
using System.ComponentModel;
using System.Runtime.InteropServices;
using System.Text;
using System.Threading;
public static class SlcTexTree {
 [StructLayout(LayoutKind.Sequential)] struct SA { public int length; public IntPtr descriptor; public int inherit; }
 [StructLayout(LayoutKind.Sequential,CharSet=CharSet.Unicode)] struct STARTUPINFO { public int cb; public string reserved; public string desktop; public string title; public int x,y,xs,ys,xc,yc,fill,flags; public short show,res2; public IntPtr reserved2,input,output,error; }
 [StructLayout(LayoutKind.Sequential)] struct PI { public IntPtr process,thread; public uint pid,tid; }
 [StructLayout(LayoutKind.Sequential)] struct BASIC { public long perProcess,perJob; public uint flags; public UIntPtr min,max; public uint active; public UIntPtr affinity; public uint priority,scheduling; }
 [StructLayout(LayoutKind.Sequential)] struct IO { public ulong ro,wo,oo,rt,wt,ot; }
 [StructLayout(LayoutKind.Sequential)] struct EXT { public BASIC basic; public IO io; public UIntPtr processMemory,jobMemory,peakProcess,peakJob; }
 [StructLayout(LayoutKind.Sequential)] struct ACCOUNT { public long user,kernel,periodUser,periodKernel; public uint faults,total,active,terminated; }
 [DllImport("kernel32.dll",CharSet=CharSet.Unicode,SetLastError=true)] static extern IntPtr CreateFile(string name,uint access,uint share,ref SA security,uint disposition,uint flags,IntPtr template);
 [DllImport("kernel32.dll",CharSet=CharSet.Unicode,SetLastError=true)] static extern bool CreateProcess(string app,StringBuilder cmd,IntPtr pa,IntPtr ta,bool inherit,uint flags,IntPtr env,string cwd,ref STARTUPINFO si,out PI pi);
 [DllImport("kernel32.dll",CharSet=CharSet.Unicode)] static extern IntPtr CreateJobObject(IntPtr a,string name);
 [DllImport("kernel32.dll")] static extern bool SetInformationJobObject(IntPtr job,int c,ref EXT info,int size);
 [DllImport("kernel32.dll",SetLastError=true)] static extern bool QueryInformationJobObject(IntPtr job,int c,out EXT info,int size,IntPtr n);
 [DllImport("kernel32.dll")] static extern bool AssignProcessToJobObject(IntPtr j,IntPtr p);
 [DllImport("kernel32.dll")] static extern uint ResumeThread(IntPtr h);
 [DllImport("kernel32.dll")] static extern bool QueryInformationJobObject(IntPtr j,int c,out ACCOUNT info,int size,IntPtr n);
 [DllImport("kernel32.dll")] static extern bool GetExitCodeProcess(IntPtr h,out uint c);
 [DllImport("kernel32.dll")] static extern bool TerminateProcess(IntPtr h,uint c);
 [DllImport("kernel32.dll")] static extern bool TerminateJobObject(IntPtr h,uint c);
 [DllImport("kernel32.dll")] static extern bool CloseHandle(IntPtr h);
 public static int Run(string app,string args,string cwd,string log,int timeout) {
  IntPtr job=CreateJobObject(IntPtr.Zero,null); if(job==IntPtr.Zero)throw new Exception("CreateJobObject failed");
  EXT limit=new EXT();limit.basic.flags=0x2200;limit.jobMemory=new UIntPtr(5000000000UL);
  PI pi=new PI();bool created=false,assigned=false;
  IntPtr output=new IntPtr(-1), input=new IntPtr(-1);
  try {
   if(!SetInformationJobObject(job,9,ref limit,Marshal.SizeOf(typeof(EXT))))throw new Exception("Job limit setup failed");
   EXT actual; var pageSize=(ulong)Environment.SystemPageSize;
   if(!QueryInformationJobObject(job,9,out actual,Marshal.SizeOf(typeof(EXT)),IntPtr.Zero)||(actual.basic.flags&0x2200)!=0x2200||actual.jobMemory.ToUInt64()!=5000000000UL/pageSize*pageSize)throw new Exception("Job memory cap verification failed");
   SA handles=new SA{length=Marshal.SizeOf(typeof(SA)),inherit=1};
   output=CreateFile(log,0x40000000,1,ref handles,2,0,IntPtr.Zero);
   if(output==new IntPtr(-1))throw new Win32Exception(Marshal.GetLastWin32Error(),"Cannot open tool log");
   input=CreateFile("NUL",0x80000000,3,ref handles,3,0,IntPtr.Zero);
   if(input==new IntPtr(-1))throw new Win32Exception(Marshal.GetLastWin32Error(),"Cannot open empty tool input");
   STARTUPINFO si=new STARTUPINFO();si.cb=Marshal.SizeOf(typeof(STARTUPINFO));si.flags=0x101;si.show=0;
   si.input=input;si.output=output;si.error=output;
   if(!CreateProcess(app,new StringBuilder("\""+app+"\" "+args),IntPtr.Zero,IntPtr.Zero,true,0x08000004,IntPtr.Zero,cwd,ref si,out pi))throw new Win32Exception(Marshal.GetLastWin32Error(),"Cannot start tool suspended");
   created=true;
   if(!AssignProcessToJobObject(job,pi.process)){TerminateProcess(pi.process,97);throw new Exception("Cannot capture owned process tree; failed closed");}
   assigned=true;if(ResumeThread(pi.thread)==0xffffffff)throw new Exception("Resume failed");
   var until=DateTime.UtcNow.AddMilliseconds(timeout);
   while(true){ACCOUNT a;if(!QueryInformationJobObject(job,1,out a,Marshal.SizeOf(typeof(ACCOUNT)),IntPtr.Zero))throw new Exception("Job accounting failed");if(a.active==0)break;if(DateTime.UtcNow>until){TerminateJobObject(job,98);throw new Exception("Owned TeX tree exceeded bounded runtime");}Thread.Sleep(150);}
   uint code;if(!GetExitCodeProcess(pi.process,out code))throw new Exception("Exit status unavailable");return (int)code;
  } finally {
   if(assigned){ACCOUNT a;if(QueryInformationJobObject(job,1,out a,Marshal.SizeOf(typeof(ACCOUNT)),IntPtr.Zero)&&a.active>0){TerminateJobObject(job,99);do {Thread.Sleep(50);if(!QueryInformationJobObject(job,1,out a,Marshal.SizeOf(typeof(ACCOUNT)),IntPtr.Zero))break;}while(a.active>0);}}
   else if(created)TerminateProcess(pi.process,99);
   if(input!=new IntPtr(-1))CloseHandle(input);if(output!=new IntPtr(-1))CloseHandle(output);
   if(pi.thread!=IntPtr.Zero)CloseHandle(pi.thread);if(pi.process!=IntPtr.Zero)CloseHandle(pi.process);CloseHandle(job);
  }
 }
}
