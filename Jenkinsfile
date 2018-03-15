node('docker') {

    withDockerContainer(
        image: 'camtango_nodb:latest',
        args: '-u root'
    ) {
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
                    sh 'nohup service mysql start'
                    sh 'nohup service tango-db start'
                    // Install the stable version 0.1.3 of pytango-devicetest
                    sh 'pip install --egg git+https://github.com/vxgmichel/pytango-devicetest.git@75c348959161b2c835b4ce6422294933c70e4915'
                    sh 'pip install nose_xunitmp'
                    sh 'pip install . -U'
                    sh 'python setup.py test --with-xunitmp --xunitmp-file nosetests.xml'
                } finally {
                    step([$class: 'JUnitResultArchiver', testResults: 'nosetests.xml'])
                }
            }
        }
    }
}
