<?php
/* Faculty of Information Technology, Brno University of Technology
*  IPP (Principles of Programming Languages) - Project 1
*  Name: IPP - IPPcode18 language testing utility
*  Date created: April 2018
*  Author: Jan Kubica
*  Login: xkubic39
*  Email: xkubic39@stud.fit.vutbr.cz
*  File: test.php - IPPcode18 test report
*/

function print_help() {
    echo "IPPcode18 LANGUAGE TESTER\n";
    echo "-------------------------";
    echo "\n";
    echo "DESCRIPTION\n";
    echo "This is simple testing utility taking test files and printing HTML report to \n";
    echo "stdout. Each test consists of 4 files, source code file, input file, output file \n";
    echo "and return code file ending with *.src, *.in, *.out and *.rc. The *.src files are \n";
    echo "required, the other files are generated automatically if missing. Native input \n";
    echo "and output is empty file, return code is 0.\n";
    echo "\n";
    echo "PARAMETERS\n";
    echo "php5.6 test.php --help                  - prints out help\n";
    echo "                --directory=<path>      - test folder\n";
    echo "                --parse-script=<file>   - parse script file, natively './parse.php'\n";
    echo "                --int-script=<file>     - interpret script file, natively './interpret.py'\n";
    echo "                --recursive             - searches for other subdirectories in test folder\n";
    echo "\n";
    echo "Made by (c)Jan Kubica (xkubic39@stud.fit.vutbr.cz), April 2018\n";
	exit(0);
}
// represents one folder with tests list
class Folder {
    public $name = "";
    public $tests = array();

    function Folder($name) {
        $this->name = $name;
    }
}

// represents one test with its attributes
class Test {
    public $name; // name
    public $ret_val; // return value
    public $ret_val_req;
    public $stderr;
    public $stdout;
    public $parser; // true x false
    public $interpret; // true x false
    public $diff; // true x false

    function Test($name) {
        $this->name = $name;
    }
}

// gets directory content and returns array
function dirContent($dir, &$results = array()){
    $files = scandir($dir);
    $cwd = getcwd();

    foreach($files as $key => $value){
        $path = realpath($dir . DIRECTORY_SEPARATOR . $value);
        if(!is_dir($path)) {
            $results[] = $path;
        } else if(!in_array($value,array(".",".."))) {
            dirContent($path, $results[$path]);
        }
    }

    return $results;
}

// gets directory array, filling $folders list with tests and creates subdirectories
function createTests($dir_list, &$rootF) {
    global $recursive;
    global $folders;
    foreach ($dir_list as $key => $value) 
    {
        if (!is_array($value)) 
        {
            if (strlen($value) > 4)
            {
                if (substr($value, -3) === "src") 
                {
                    $n = substr($value, 0, -4);
                    $t = new Test($n);
                    array_push($rootF->tests, $t);
                }
            }
        }
        else if ($recursive) {
            $f = new Folder($key);
            array_push($folders, $f);
            createTests($value, $f);
        }      
    }
}

// run all tests in given folder
function runTestFolder($folder) {
    global $parser_file, $interpret_file;
    foreach ($folder->tests as $test)
    {
        $parser_finished = "FAIL";
        $interpret_finished = "FAIL";
        $output = "";
        $ret_val = 0;
        $diff = false;

        // create missing files
        if (!file_exists($test->name.".rc"))
        {
            file_put_contents($test->name.".rc", "0");
        }
        if (!file_exists($test->name.".in"))
        {
            touch($test->name.".in");
        }
        if (!file_exists($test->name.".out"))
        {
            touch($test->name.".out");
        }

        $stdout1_fd = tmpfile();
        $stdout2_fd = tmpfile();
        $stderr_fd = tmpfile();
        
        $stdout1_m = stream_get_meta_data($stdout1_fd);
        $stdout2_m = stream_get_meta_data($stdout2_fd);
        $stderr_m = stream_get_meta_data($stderr_fd);

        $stdout1_file = $stdout1_m['uri'];
        $stdout2_file = $stdout2_m['uri'];
        $stderr_file = $stderr_m['uri'];

        // execute parser
        exec("php5.6 ".$parser_file." <".$test->name.".src 1>".$stdout1_file." 2>".$stderr_file,$output,$ret_val);

        $stdout = file_get_contents($stdout1_file);
        $stderr = file_get_contents($stderr_file);

        // if success, execute interpret
        if (strlen($stderr) === 0) 
        {
            $parser_finished = "OK";

            exec("python3.6 ".$interpret_file." --source=".$stdout1_file." <".$test->name.".in"." 1>".$stdout2_file." 2>".$stderr_file,$output,$ret_val);
            
            $stdout = file_get_contents($stdout2_file);
            $stderr = file_get_contents($stderr_file);

            if (strlen($stderr) == 0 || $ret_val == 0) 
            {
                $interpret_finished = "OK";
            }
            exec("diff ".$stdout2_file." ".$test->name.".out",$output);
            if (empty($output)) {
                $diff = "OK";
            }
            else {
                $diff = "FAIL";
            }

        } else {
            $interpret_finished = "-";
        }

        $ret_val_req = file_get_contents($test->name.".rc");

        $test->ret_val = $ret_val;
        $test->ret_val_req = $ret_val_req;
        $test->stderr = $stderr;
        $test->stdout = $stdout;
        $test->parser = $parser_finished;
        $test->interpret = $interpret_finished;
        $test->diff = $diff;

        fclose($stderr_fd);
        fclose($stdout1_fd);
        fclose($stdout2_fd);
    }
}

// ------- MAIN ---------

$longopts = array(
    "help",
    "directory:",
    "recursive",
    "parse-script:",
    "int-script:",
);

$options = getopt("hd:rp:i:", $longopts);

// RESOLVE argument options
if (isset($options['parse-script'])) {
    $parser_file = $options['parse-script'];
} else {
    $parser_file = "./parse.php";
}
if (isset($options['int-script'])) {
    $interpret_file = $options['int-script'];
} else {
    $interpret_file = "./interpret.py";
}
if (isset($options['directory'])) {
    $root_path = $options['directory'];
} else {
    $root_path = getcwd();
}
if (isset($options["recursive"])) {
    $recursive = true;
} else {
    $recursive = false;
}
if (isset($options["help"])) {
    print_help();
}

if (file_exists($root_path))
    $dir_list = dirContent($root_path);
else {
    fwrite(STDERR, "ERROR: Given path not found\n");
    exit(11);
}

$folders = array();
$root_folder = new Folder($root_path);
array_push($folders, $root_folder);

// look for tests in directory
createTests($dir_list, $root_folder);

// run tests
foreach ($folders as $folder)
    runTestFolder($folder);

// print result
echo "<!DOCTYPE html>"."\n";
echo "<html>"."\n";
echo "   <head>"."\n";
echo '      <meta charset="UTF-8">'."\n";
echo "      <title>Test Report</title>"."\n";
echo "   </head>"."\n";
echo "   <body>"."\n";
echo "      <h1>IPPcode18 - Test report</h1>\n";
echo '      <p>'."\n";
echo '      Test script: <b>' . __FILE__ . "</b><br>\n";
echo '      Root folder: <b>' . $root_path . "</b><br>\n";
echo '      Parser: <b>' . $parser_file . "</b><br>\n";
echo '      Interpret: <b>' . $interpret_file . "</b><br>\n";
echo '      Recursive search: <b>'; echo $recursive ? 'true' : 'false'; echo "</b><br>\n";
echo '      </p>'."\n";
echo "      <h3>Test results:</h3>\n";

$succ_all = 0;
$test_all = 0;
foreach ($folders as $folder) {
    echo '      <table style="width:100%" border="1"><thead>'."\n";

    echo '         <tr><td colspan="8" style="padding:5px">Folder: <b>'.$folder->name.'</b></td></tr>'."\n";

    echo "         <tr>"."\n";       
    echo '            <th>' . "Test name" .'</th>'."\n";
    echo '            <th>' . "Parser processed" .'</th>'."\n";
    echo '            <th>' . "Interpret processed" .'</th>'."\n";
    echo '            <th>' . "Return code" .'</th>'."\n";
    echo '            <th>' . "Return code requested" .'</th>'."\n";
    echo '            <th>' . "Stdout diffcheck" .'</th>'."\n";
    echo '            <th>' . "Stdout" .'</th>'."\n";
    echo '            <th>' . "Stderr" .'</th>'."\n";
    echo '         </tr></thead>'."\n";
    echo "      <tbody>"."\n";

    $success = 0;

    foreach ($folder->tests as $test)
    {
        $i = strrpos($test->name, DIRECTORY_SEPARATOR);
        echo '         <tr>'."\n";
        if ($test->diff == "OK" && $test->ret_val == $test->ret_val_req) {
            echo '            <td align="center" bgcolor="#00FF00" style="padding:5px">'.substr($test->name,$i+1,strlen($test->name)-$i).'</td>'."\n";
            $success +=1;
        }
        else {
            echo '            <td align="center" bgcolor="#FF0000" style="padding:5px">'.substr($test->name,$i+1,strlen($test->name)-$i).'</td>'."\n";
        }
        echo '            <td align="center">'.$test->parser.'</td>'."\n";
        echo '            <td align="center">'.$test->interpret.'</td>'."\n";
        echo '            <td align="center">'.$test->ret_val.'</td>'."\n";
        echo '            <td align="center">'.$test->ret_val_req.'</td>'."\n";
        echo '            <td align="center">'.$test->diff.'</td>'."\n";
        echo '            <td style="padding:5px"><pre>'.$test->stdout.'</pre></td>'."\n";
        echo '            <td style="padding:5px"><pre>'.$test->stderr.'</pre></td>'."\n";
        echo '         </tr>'."\n";
    }
    echo '         <tr><td align="right" colspan="8" style="padding:5px">Succeded <b>'.$success.'</b> of '.count($folder->tests).' tests.</td></tr>'."\n";
    $succ_all += $success;
    $test_all += count($folder->tests);
    $success = 0;
    echo "<br>";

}

echo '      </tbody></table>'."\n";
echo '      <h3 align="right">In total: '.$succ_all." of ".$test_all." tests succeded</h3>";
echo "   </body>"."\n";
echo "</html>"."\n";

?>