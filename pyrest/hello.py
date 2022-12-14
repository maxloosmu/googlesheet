from flask import Flask, request, send_from_directory, render_template, send_file
import sys, string, os, datetime, glob, shutil, subprocess, re, json
from pathlib import Path

# template_dir = "/Users/maxloo/googlesheet/pyrest/template/"
# temp_dir = "/Users/maxloo/googlesheet/pyrest/temp/"
# static_dir = "/Users/maxloo/googlesheet/pyrest/static/"
template_dir = "/mnt/c/Users/Max/src/googlesheet/pyrest/template/"
temp_dir = "/mnt/c/Users/Max/src/googlesheet/pyrest/temp/"
static_dir = "/mnt/c/Users/Max/src/googlesheet/pyrest/static/"
app = Flask(__name__, template_folder=template_dir, static_folder=static_dir)

@app.route("/corel4/<uuid>/<ssid>/<sid>")
def getCorel4File(uuid, ssid, sid):
  textStr = ""
  corel4Folder = temp_dir + "workdir/" + uuid + "/" + ssid + "/" + sid + "/corel4/"
  with open(corel4Folder + "LATEST.l4", "r") as fin:
    for line in fin.readlines():
      textStr = textStr + line
  return render_template("corel4.html", data=textStr)

@app.route("/petri/<uuid>/<ssid>/<sid>")
def getPetriFile(uuid, ssid, sid):
  petriFolder = temp_dir + "workdir/" + uuid + "/" + ssid + "/" + sid + "/petri/"
  dotPath = petriFolder + "LATEST.dot"
  if not os.path.exists(petriFolder):
    Path(petriFolder).mkdir(parents=True, exist_ok=True)
  petriPath = petriFolder + "LATEST.png"
  return render_template("petri.html",
                         uuid = uuid,
                         ssid = ssid,
                         sid  = sid )

# secondary handler used by
#######  the petri template img src ... and others

# [TODO] we probably want to also just make the filename fully explicit to defeat caching

@app.route("/workdir/<uuid>/<ssid>/<sid>/<channel>/<filename>")
def getWorkdirFile(uuid, ssid, sid, channel, filename):
  workdirFolder = temp_dir + "workdir/" + uuid + "/" + ssid + "/" + sid + "/" + channel
  if not os.path.exists(workdirFolder):
    print("getWorkdirFile: unable to find workdirFolder " + workdirFolder, file=sys.stderr)
    return;
  if not os.path.isfile(workdirFolder + "/" + filename):
    print("getWorkdirFile: unable to find file %s/%s"  % (workdirFolder, filename), file=sys.stderr)
    return;
  (fn,ext) = os.path.splitext(filename)
  if (ext == ".l4"
      or ext == ".epilog"
      or ext == ".purs"
      or ext == ".org"
      or ext == ".hs"
      or ext == ".ts"
      ):

    print("getWorkdirFile: returning text/plain %s/%s" % (workdirFolder, filename), file=sys.stderr)
    return send_file(workdirFolder + "/" + filename, mimetype="text/plain")
  else:
    print("getWorkdirFile: returning %s/%s" % (workdirFolder, filename), file=sys.stderr)
    return send_file(workdirFolder + "/" + filename)

@app.route("/aasvg/<uuid>/<ssid>/<sid>/<image>")
def showAasvgImage(uuid, ssid, sid, image):
  print("showAasvgImage: handling /aasvg/ url", file=sys.stderr);
  aasvgFolder = temp_dir + "workdir/" + uuid + "/" + ssid + "/" + sid + "/aasvg/LATEST/"
  imagePath = aasvgFolder + image
  print("showAasvgImage: sending path " + imagePath, file=sys.stderr)
  return send_file(imagePath)


@app.route("/post", methods=['GET', 'POST'])
def processCsv():
  data = request.form.to_dict()

  response = {}

  uuid = data['uuid']
  spreadsheetId = data['spreadsheetId']
  sheetId = data['sheetId']
  # targetFolder = "/Users/maxloo/googlesheet/pyrest/temp/workdir/"+uuid+"/"+spreadsheetId+"/"+sheetId+"/"
  targetFolder = "/mnt/c/Users/Max/src/googlesheet/pyrest/temp/workdir/"+uuid+"/"+spreadsheetId+"/"+sheetId+"/"
  print(targetFolder)
  timeNow = datetime.datetime.utcnow().strftime("%Y%m%dT%H%M%S.%fZ")
  targetFile = timeNow + ".csv"
  targetPath = targetFolder + targetFile
  # if not os.path.exists(targetFolder):
  Path(targetFolder).mkdir(parents=True, exist_ok=True)

  with open(targetPath, "w") as fout:
    fout.write(data['csvString'])

  # targetPath is for CSV data
  # createFiles = "natural4-exe --workdir=/Users/maxloo/googlesheet/pyrest/temp/workdir --uuiddir=" + uuid + "/" + spreadsheetId + "/" + sheetId + " " + targetPath
  createFiles = "natural4-exe --workdir=/mnt/c/Users/Max/src/googlesheet/pyrest/temp/workdir --uuiddir=" + uuid + "/" + spreadsheetId + "/" + sheetId + " " + targetPath
  # createFiles = "natural4-exe --workdir=/home/mengwong/pyrest/temp/workdir --uuiddir=" + uuid + " --topetri=petri --tojson=json --toaasvg=aasvg --tonative=native --tocorel4=corel4 --tocheckl=checklist  --tots=typescript " + targetPath
  print("hello.py main: calling natural4-exe", file=sys.stderr)
  print("hello.py main: %s" % (createFiles), file=sys.stderr)
  nl4exe = subprocess.run([createFiles], shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
  print("hello.py main: back from natural4-exe", file=sys.stderr)
  print("hello.py main: natural4-exe stdout length = %d" % len(nl4exe.stdout.decode('utf-8')), file=sys.stderr)
  print("hello.py main: natural4-exe stderr length = %d" % len(nl4exe.stderr.decode('utf-8')), file=sys.stderr)

  if len(nl4exe.stderr.decode('utf-8')) < 2000:
    print (nl4exe.stderr.decode('utf-8'))
  nl4_out = nl4exe.stdout.decode('utf-8')

  response['nl4_stderr'] = nl4exe.stderr.decode('utf-8')[:20000]
  response['nl4_stdout'] = nl4exe.stdout.decode('utf-8')[:20000]

  #
  # postprocessing after running natural4-exe:
  #   postprocessing for petri nets:
  #     turn the DOT files into PNGs

  uuidssfolder = temp_dir + "workdir/" + uuid + "/" + spreadsheetId + "/" + sheetId
  petriFolder = uuidssfolder + "/petri/"
  dotPath = petriFolder + "LATEST.dot"
  (timestamp,ext) = os.path.splitext(os.readlink(dotPath));

  if not os.path.exists(petriFolder):
    print("expected to find petriFolder %s but it's not there!" % (petriFolder), file=sys.stderr);
  else:
    petriPath = petriFolder + timestamp + ".png"
    smallPetriPath = petriFolder + timestamp + "-small.png"
    print("hello.py main: running: dot -Tpng -Gdpi=150 " + dotPath + " -o " + petriPath + " &", file=sys.stderr)
    os.system("dot -Tpng -Gdpi=72  " + dotPath + " -o " + smallPetriPath + " &")
    os.system("dot -Tpng -Gdpi=150 " + dotPath + " -o " + petriPath + " &")
    try:
      if os.path.isfile(petriFolder + "LATEST.png"):       os.unlink(                 petriFolder + "LATEST.png")
      if os.path.isfile(petriFolder + "LATEST-small.png"): os.unlink(                 petriFolder + "LATEST-small.png")
      os.symlink(os.path.basename(petriPath),      petriFolder + "LATEST.png")
      os.symlink(os.path.basename(smallPetriPath), petriFolder + "LATEST-small.png")
    except Exception as e:
      print("hello.py main: got some kind of OS error to do with the unlinking and the symlinking", file=sys.stderr);
      print("hello.py main: %s" % (e), file=sys.stderr);

    #   postprocessing for the babyl4 downstream transpilations
    #     call l4 epilog corel4/LATEST.l4

    corel4Path = uuidssfolder + "/corel4/LATEST.l4"
    epilogPath = uuidssfolder + "/epilog"
    Path(epilogPath).mkdir(parents=True, exist_ok=True)
    epilogFile = epilogPath + "/" + timeNow + ".epilog"

    print("hello.py main: running: l4 epilog " + corel4Path + " > " + epilogFile, file=sys.stderr)
    os.system("l4 epilog " + corel4Path + " > " + epilogFile + " &")
    if os.path.isfile(epilogPath + "/LATEST.epilog"): os.unlink( epilogPath + "/LATEST.epilog")
    os.symlink(timeNow + ".epilog", epilogPath + "/LATEST.epilog")

    #   postprocessing for the vue web server
    #     call v8k up

    # v8kargs = ["/Users/maxloo/googlesheet/pyrest/bin/python", "/Users/maxloo/vue-pure-pdpa/bin/v8k", "up",
    v8kargs = ["/mnt/c/Users/Max/src/googlesheet/pyrest/bin/python", "/root/src/vue-pure-pdpa/bin/v8k", "up",
               "--uuid="    + uuid,
               "--ssid="    + spreadsheetId,
               "--sheetid=" + sheetId,
               uuidssfolder + "/purs/LATEST.purs"]

    print("hello.py main: calling %s" % (" ".join(v8kargs)), file=sys.stderr)
# v8k = subprocess.run(v8kargs,
#                            stdout=subprocess.PIPE,
#                            stderr=subprocess.PIPE
#    )
    os.system(" ".join(v8kargs) + "> " + uuidssfolder + "/v8k.out");
    print("hello.py main: v8k up returned", file=sys.stderr)
    with open(uuidssfolder + "/v8k.out", "r") as read_file:
      v8k_out = read_file.readline();
    print("v8k.out: %s" % (v8k_out), file=sys.stderr)

    # v8k_out = v8k.stdout.decode('utf-8')

    if re.match(r':\d+', v8k_out): # we got back the expected :8001/uuid/ssid/sid whatever from the v8k call
      v8k_url = v8k_out.strip()
      print("v8k up succeeded with: " + v8k_url, file=sys.stderr)
      response['v8k_url'] = v8k_url
    else:
      v8k_url = ""
      response['v8k_url'] = None
      #      v8k_error = v8k.stderr.decode('utf-8')
      #      print("hello.py main: v8k up stderr: " + v8k_error,                  file=sys.stderr)
      #      print("hello.py main: v8k up stdout: " + v8k.stdout.decode('utf-8'), file=sys.stderr)

    with open(uuidssfolder + "/aasvg/LATEST/index.html", "r") as read_file:
      response['aasvg_index'] = read_file.read();

  response['timestamp'] = timestamp;

  print("hello.py main: returning", file=sys.stderr)
  # print(json.dumps(response), file=sys.stderr)
  return json.dumps(response)

@app.route("/you/<name>")
def user(name):
  return """
      <!DOCTYPE html>
      <html>
      <head><title>Hello</title></head>
      <body><h1>Hello, {name}</h1></body>
      </html>
      """.format(name=name), 200

@app.route("/")
def hello():
  return "Hello World!"

if __name__ == '__main__':
  app.run(host='0.0.0.0', port=8080, debug=False, threaded=True, processes=6)


