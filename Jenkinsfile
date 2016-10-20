node('Slave433') {

    stage 'Cleanup workspace'
    sh 'chmod 777 -R .'
    sh 'rm -rf *'

    stage 'Checkout SCM'
        checkout([
            $class: 'GitSCM',
            branches: [[name: "refs/heads/${env.BRANCH_NAME}"]],
            extensions: [[$class: 'LocalBranch']],
            userRemoteConfigs: scm.userRemoteConfigs,
            doGenerateSubmoduleConfigurations: false,
            submoduleCfg: []
        ])

    stage 'Install & Unit Tests'
        timestamps {
            timeout(time: 30, unit: 'MINUTES') {
                try {
                    sh 'service tango-db restart'
                    sh 'virtualenv venv'
                    sh 'source venv/bin/activate'
                    sh 'pip install --egg git+https://github.com/tango-cs/PyTango.git@develop'
                    sh 'pip install . -U'
                    sh 'pip install pip install nose_xunitmp nosexcover -U'
                    sh 'nosetests -v --with-xunitmp --xunitmp-file=nosetests.xml  --processes=1 --process-restartworker --process-timeout=400 .'
                } finally {
                    step([$class: 'JUnitResultArchiver', testResults: 'nosetests.xml'])
                }
            }
        }
}
