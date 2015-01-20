#!/usr/bin/python


# USAGE:
# ./runTests /share/dev/test/applications
# to scan through all folders in the applications directory and run all tests located,
# where a test is a set of 1 job submission script (.ll or .sl), 1 python point check script, and all files the job depends on

# ./runTests myTests.txt
# where myTests.txt contains a line separated list of paths to folders containing tests


# EXAMPLE test script:
#### #!/usr/bin/python
#### import os, sys, subprocess
#### filePath = sys.argv[1]
#### p = subprocess.Popen("cat " + filePath, stdout = subprocess.PIPE, shell=True)
#### (answer, err)  = p.communicate()
#### if "3565" in answer:
#### 	print 1
#### else: print 0

# where 3565 is an expected output indicating the successful completion of the co-located job


import os, sys, filecmp, re, shutil, time, subprocess, os.path, argparse

class TestJob:
        jobCount = 0
        failCount = 0
        passCount = 0
        scriptCount = 0

	def __init__(self, pathToJob, pathToScripts, job, jobType, program):
                self.program = program
                self.pathToLL = pathToJob
                self.jobType = jobType
                self.job = job
                self.pathToScripts = pathToScripts
                TestJob.jobCount += 1
                self.testScripts = []
                self.scriptResults = []
                self.report = job + program +  jobType

	def addTestScript(self, testScript):
                self.testScripts.append(testScript)
                TestJob.scriptCount += 1

	def addScriptResult(self, result): self.scriptResults.append(result)
        def setLocalPath(self, localPath): self.localPath = localPath
        def setLocalLL(self, localLL): self.localLL = localLL
        def setID(self, ID): self.ID = ID
        def writeReport(self, report): self.report = report
        def writeScriptReport(self, report): self.scriptReport = report



# crawl through directory searching appropriate jobs files
def findJobs():
        listOfJobs = []
        listOfLLs = []
        for dir in os.listdir(applicationsDir):
                #if "TEST" in dir.upper():
                root = os.path.join(applicationsDir, dir)
                for file in os.listdir(root):
                        if os.path.splitext(file)[1] == ".ll":
                                # ensure .ll file is intended as a job

				jobType = "ll"
                                listOfLLs.append([root, file, jobType, dir])

			if os.path.splitext(file)[1] == ".sl":
                                # ensure .sl file is intended as a job
                                jobType = "sl"
                                listOfLLs.append([root, file, jobType, dir])

		# ensure .ll file has corresponding test script
                for pathInfo in listOfLLs:

		LLfile = pathInfo[0]
                for file in os.listdir(LLfile):
                        if os.path.splitext(file)[1] == ".py":
                                newJob = TestJob(LLfile, file, pathInfo[1], pathInfo[2], pathInfo[3])
                                newJob.addTestScript(file)
                                listOfJobs.append(newJob)
                                break

	return listOfJobs

# create local copies of jobs, and modifies their output paths
def copyAndModifyJobsLL(listOfJobs):
        for job in listOfJobs:
                p = subprocess.Popen("mkdir " + os.path.join(localJobsDir, job.program) , stdout = subprocess.PIPE, stderr = subprocess.PIPE, shell=True)
                p.communicate()
                for file in os.listdir(job.pathToLL):
                        if os.path.isdir(os.path.join(job.pathToLL,file)):
                                shutil.copytree(os.path.join(job.pathToLL,file), os.path.join(localJobsDir, os.path.join(job.program, file)))
else:
        shutil.copyfile(os.path.join(job.pathToLL, file), os.path.join(localJobsDir, os.path.join(job.program, file)))

	for job in listOfJobs:
                if job.jobType == 'll':
                        jobName = job.job
                        jobType = job.jobType
                        localLoc = os.path.join(localJobsDir, job.program)
                        pathToFile = os.path.join(job.pathToLL, os.path.join(job.pathToLL, jobName))

			filesDir = os.path.join(job.pathToLL, "files")
                        if os.path.isdir(filesDir):
                                if os.listdir(filesDir) != []:
                                        for myfile in os.listdir(filesDir):
                                                if not os.path.isdir(myfile):
                                                        filePath = os.path.join(filesDir, myfile)
                                                        shutil.copyfile(filePath, localJobsDir + "/" + myfile)

			jobPath = os.path.join(localJobsDir, os.path.join(job.program, jobName))

			job.setLocalPath(jobPath)
                        job.setLocalLL(jobPath)
                        f = open(jobPath, 'r+b')
                        fText = f.read()
                        fText = re.sub('#@ initialdir.*', "#@ initialdir = " + currDir + "/localJobs/" + job.program, fText)
                        fText = re.sub('#@ output.*', "#@ output = ../../actualOutput/" + jobName[0:len(jobName)-3] + ".txt", fText)
                        fText = re.sub('#@ error.*', "#@ error = ../../errors/" + jobName[0:len(jobName)-3] + ".txt", fText)
                        f.seek(0)	# seek and truncate needed, or just appends new lines to bottom
                        f.truncate()
                        f.write(fText)
                        f.close()


def copyAndModifyJobsSL(listOfJobs):
        for job in listOfJobs:
                if job.jobType == 'sl':
                        jobName = job.job
                        jobType = job.jobType
                        localLoc = os.path.join(localJobsDir, job.program)
                        pathToFile = os.path.join(job.pathToLL, os.path.join(job.pathToLL, jobName))

			filesDir = os.path.join(job.pathToLL, "files")
                        if os.path.isdir(filesDir):
                                if os.listdir(filesDir) != []:
                                        for myfile in os.listdir(filesDir):
                                                if not os.path.isdir(myfile):
                                                        filePath = os.path.join(filesDir, myfile)
                                                        shutil.copyfile(filePath, localJobsDir + "/" + myfile)
                                                        jobPath = os.path.join(localJobsDir, os.path.join(job.program, jobName))

			job.setLocalPath(jobPath)
                        job.setLocalLL(jobPath)
                        f = open(jobPath, 'r+b')
                        fText = f.read()
                        fText = re.sub('#!/bin/bash.*', "", fText)
                        fText = re.sub('#SBATCH -o.*', "", fText)
                        fText = re.sub('#SBATCH -e.*', "", fText)
                        f.seek(0)	# seek and truncate needed or just appends new lines to bottom
                        f.truncate()
                        f.write("#!/bin/bash\n")
                        f.write("#SBATCH -o SLURM" + jobName[0:len(jobName)-3] + ".txt\n")
                        f.write("#SBATCH -e SLURM" + jobName[0:len(jobName)-3] + ".txt\n")
                        f.write(fText)
                        f.close()



def LLsubmit(jobsList):
        for job in jobsList:
                if job.jobType == 'll':

		#	testFile = job.localLL
                        localJobPath = os.path.join(currDir, "localJobs", job.program)
                        os.chdir(os.path.join(currDir, "localJobs", job.program))
                        testFile = job.localLL
                        temp = testFile.split("/")
                        testFile = temp[len(temp)-1]
                        ##1 = subprocess.Popen("pwd", stdout = subprocess.PIPE, shell=True)
                        ##(cdir, err)  = p1.communicate()
                        ##print cdir
                        p = subprocess.Popen("llsubmit " + testFile , stdout = subprocess.PIPE, stderr = subprocess.PIPE, shell=True)
                        (LLout, err)  = p.communicate()
                        if 'submitted' in LLout:
                                jobId = LLout[19:35]
else:
        jobId = "SUBMITFAILED"

			job.setID(jobId)
                        os.chdir(realDir)


def SLsubmit(jobsList):
        for job in jobsList:
                if job.jobType == 'sl':

			localJobPath = os.path.join(currDir, "localJobs", job.program)
                        os.chdir(os.path.join(currDir, "localJobs", job.program))
                        testFile = job.localLL
                        temp = testFile.split("/")
                        testFile = temp[len(temp)-1]


			p = subprocess.Popen("sbatch " + testFile , stdout = subprocess.PIPE, stderr = subprocess.PIPE, shell=True)
                        (SLout, err)  = p.communicate()

			if 'Submitted' in SLout:
                                jobId = SLout[19:35]
else:
        jobId = "SUBMITFAILED"
        job.setID(jobId)
        os.chdir(realDir)


# wait for job completion and output file writing
def processOutputLL(jobsList):
        for job in jobsList:
                if job.jobType == 'll':
                        if 'FAILED' in job.ID:
                                job.writeReport("Submission to LL failed")
                                break
else:
        if verbose == 1:
                print(job.program + ":")
                os.system("/share/bin/llwait " + job.ID)



def processOutputSL(jobsList):
        for job in jobsList:
                if job.jobType == 'sl':
                        skip = 0
                        if "SUBMITFAILED" in job.ID:
                                job.writeReport("Submission to SLURM failed")
                                skip = 1
                                cc = 0
                                while True:
                                        if skip == 1:
                                                break

				p = subprocess.Popen("sacct | grep " + job.ID, stdout = subprocess.PIPE, stderr = subprocess.PIPE, shell=True)
                                (completed, err) = p.communicate()

				if "CANCELLED" in completed:
                                        job.writeReport("SLURM job cancelled")
                                        break
                                if "FAILED" in completed:
                                        job.writeReport("SLURM job cancelled")
                                        break
                                if verbose==1:
                                        if cc >= 6:
                                                cc = 0
                                                print "waiting on SLURM job " + job.ID # + " " + job.program
                                                cc = cc + 2
                                                if "RUNNING" in completed:
                                                        time.sleep(1)
elif "COMPLETED" in completed:
        break
time.sleep(2)


	for job in jobsList:
                if job.jobType == 'sl':
                        actualFile = os.path.join(actualOutputDir, job.job[0:len(job.job)-3] + ".txt")
                        localOutput = os.path.join(localJobsDir, os.path.join(job.program, "SLURM"+job.job[0:len(job.job)-3] + ".txt"))

			acc = 0
                        while not (os.path.isfile(localOutput)):
                                if 'failed' in job.report:
                                        break
                                acc = acc + 2
                                time.sleep(2)
                                if (acc > 5):
                                        print("waiting on job: " + job.program)
                                        os.system("sacct -j " + job.ID)
                                        acc = 0
                                        time.sleep(2)
                                        os.system("cp " + localOutput + " " + actualFile)

# run python point-check scripts on the outputs


def runTests(jobsList):
        for job in jobsList:
                for script in job.testScripts:
                        scriptPath = os.path.join(localJobsDir, os.path.join(job.program, job.pathToScripts))

			actualFile = os.path.join(actualOutputDir, job.job[0:len(job.job)-3] + ".txt")

			proc = subprocess.Popen("python " + scriptPath + " " + actualFile, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
                        err = ""
                        (answer, err) = proc.communicate()
                        #print scriptPath + " " + actualFile
                        #print err
                        #print answer
                        answer = answer.strip()
                        if (answer=="1") or (answer.upper()=="TRUE") or (answer==1):
                                job.addScriptResult(job.program + " script " +  script + ": successful")
elif (answer=="0") or (answer.upper()=="FALSE") or (answer==0):
        job.addScriptResult(job.program + " script " +  script + ": failed")
else:
        job.addScriptResult(job.program + " script " + script + ": job submission failed ")


# write report
def writeScriptReport(jobsList):
        testReportPath = os.path.join(currDir, "testReport.txt")
        if os.path.isfile(testReportPath):
                os.system("rm " + testReportPath)
                os.system("touch " + testReportPath)

	wholeReport = ""
        for job in jobsList:
                for result in job.scriptResults:
                        wholeReport = wholeReport + result + "\n"

	reportFile = os.path.join(currDir, "testReport.txt")
        f = open(reportFile, 'r+b')
        f.write("programs tested: " + str(TestJob.jobCount) + "\n scripts tested: "+ str(TestJob.scriptCount) + "\n" + wholeReport)
        f.close()
        if verbose==1:
                os.system("cat " + reportFile)



####################################################################################

p = subprocess.Popen("pwd", stdout = subprocess.PIPE, shell=True)
(currDir, err)  = p.communicate()
currDir = currDir.strip()
realDir = currDir

parser = argparse.ArgumentParser()
parser.add_argument("mainInput", help="a directory containing test directories (a python script, a job, and any files the job depends on), or a text file containing a line separated list of paths to test directories")
parser.add_argument("-v", "--verbose", help="display output and job queue pings when waiting")


args = parser.parse_args()
verbose = 0
if args.verbose:
        verbose = 1

if args.verbose == 1:
        verbose = 1

mainInput = args.mainInput

temp = os.path.splitext(mainInput)
if temp[len(temp)-1] == "txt":
        mode = "file"

if os.path.isdir(mainInput):
        mode = "folder"
else:
        mode = "file"

# set up paths relative to input directory
if mode == "folder":
        currDirSuper = mainInput
        currDir = os.path.join(currDirSuper, "testFolder")

# set up paths relative to temporary directory, and copy all listed jobs into
if mode == "file":
        subsetTestsDir = os.path.join(realDir, "subsetTests")
        subsetFile = mainInput
        f = open(subsetFile, 'r+b')

	temp = mainInput.split("/")
        inputDir = temp[0:(len(temp)-1)]
        subsetList = f.readlines()
        if os.path.isdir(subsetTestsDir):
                os.system("rm -r " + subsetTestsDir)
                os.system("mkdir " + subsetTestsDir)
                for test in subsetList:
                        if len(test.replace(" ","")) < 2:
                                continue
                        if test[0] == "#":
                                continue
                        temp = test.split("/")
                        test=test.strip()

		os.system("cp -r " + test + " " + os.path.join(subsetTestsDir, temp[len(temp)-1]))

	f.close()
        currDir = os.path.join(subsetTestsDir, "testFolder")


os.system("mkdir -p " + currDir)
os.system("cd " + currDir)

p1 = subprocess.Popen("id", stdout = subprocess.PIPE, shell=True)
(userId, er1) = p1.communicate()
userId = userId[9:16] # LoadLeveler

# set up directory paths
applicationsDir = os.path.join(currDir, "..")
localJobsDir = os.path.join(currDir, "localJobs")
if os.path.isdir(localJobsDir):
        os.system("rm -r " + localJobsDir)
        actualOutputDir = os.path.join(currDir, "actualOutput/")
        expectedOutputDir = os.path.join(currDir, "expectedOutput/")
        testResultsDir = os.path.join(currDir, "testResults/")


errors = os.path.join(currDir, "errors/")

# for quick tests, allow grouping within ./miscProgs

os.system("mkdir -p " + localJobsDir + " " + actualOutputDir + " " + expectedOutputDir + " " + errors)
os.system("rm -f " + actualOutputDir + "*.txt")

# do bulk of work
jobsList = findJobs()
copyAndModifyJobsLL(jobsList)
copyAndModifyJobsSL(jobsList)
LLsubmit(jobsList)
SLsubmit(jobsList)
time.sleep(2)
processOutputLL(jobsList)
processOutputSL(jobsList)
runTests(jobsList)
writeScriptReport(jobsList)

### cleanup: should just not do deprecated expectedOutput checks

fileReportPath = os.path.join(currDir, "fileReport.txt")
#####os.system("rm -r " + localJobsDir + " " + expectedOutputDir)


if mode == "file":
        if ".txt" in mainInput:
                mainInput = mainInput[0:(len(mainInput)-4)]

if mode == "folder":
        temp = mainInput.split("/")
        mainInput = temp[len(temp)-1]

testOutDir =  os.path.join(realDir, "test_out_" + mainInput)
#testOutDir = os.path.join(realDir, "test_out")

# clean up
if os.path.isdir(testOutDir):
        os.system("rm -r " + testOutDir)
        os.system("cp -r " + currDir + " " + testOutDir)
        os.system("rm -r " + currDir)

if mode == "file":
        os.system("rm -r " + subsetTestsDir)
