/*
This program runs uptests on a given proc and emits JSON containing the uptest
results to stdout.

Usage:

    uptester <folder> <host> <port>

Where 'folder' contains uptest scripts for the proc, and 'host' and 'port' tell
the uptests where to connect if the proc is a network service.

Uptests must be run in an environment that is identical to the real proc,
meaning the same env vars, libraries, and container setup.  

The uptester program has been written in Go for two reasons:

1. Unlike Python, Go programs are compiled and easy to statically link so
they'll run in any Linux environment, regardless of env vars or installed
libraries.

2. Go is cleaner, safer, and easier to write than C.  It has garbage
collection.  It has no pointer arithmetic.  It has JSON in the standard
library.

If you are going to make changes to this program and check them back in to
libraptor, please make sure you also check in a newly-compiled binary.  You can
compile it like this:

    go build uptester.go

The version included with libraptor must be compiled on Linux.
*/

package main

import (
    "fmt"
    "os"
    "os/exec"
    "flag"
    "strings"
    "io/ioutil"
    "path"
    "encoding/json"
)

// The JSON dumper will only extract a struct's values if they're public
// (capitalized).  It's annoying that they have to be capitalized in the JSON
// output, but whatever.
type Result struct {
    Name string
    Output string
    Passed bool
}

func UptestProc(file string, host string, port string) Result {
    cmd := exec.Command(file, host, port)
    out, err := cmd.CombinedOutput()
    r := Result{
        Name: path.Base(file),
        Output: string(out)}

    if err != nil {
        r.Passed = false
        // If the command returned no output, then use the error string as
        // output so users will see the "permission denied", for example
        if r.Output == "" {
            r.Output = err.Error()
        }
    } else {
        // I don't know whether there are situations where
        // ProcessState.Success() would be false but no error would be raised
        // from cmd.CombinedOutput(), but fetching the pass status explicitly
        // ensures that we would catch such a case if it happened.
        r.Passed = cmd.ProcessState.Success()
    }
    return r
}

func main() {
    // parse cmd line arguments and ensure we've been passed the right number
    // of them.
    flag.Parse()
    if len(flag.Args()) != 3 {
        fmt.Println("Usage: uptester <folder> <host> <port>")
        os.Exit(1)
    }
    folder := flag.Arg(0)
    host := flag.Arg(1)
    port := flag.Arg(2)

    // Get the contents of the specified folder.
    dir, err := ioutil.ReadDir(folder)
    if err != nil {
        fmt.Println(err)
        os.Exit(1)
    }

    // make a slice to hold results
    results := []Result{}

    // loop over files in folder, execute each with hostname and port
    // arguments, and append to results.
    for _, file := range dir {
        // filter out hidden files
        if strings.Index(file.Name(), ".") != 0 {
            fullpath := path.Join(folder, file.Name())
            results = append(results, UptestProc(fullpath, host, port))
        }
    }
    formatted, err := json.Marshal(results)
    if err != nil {
        fmt.Println(err)
        os.Exit(1)
    } else {
        fmt.Printf(string(formatted) + "\n")
    }
}

