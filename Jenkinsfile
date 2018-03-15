node('docker') {

    withDockerContainer(
        image: 'camtango_db:latest',
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
                    sh 'nohup service mysql restart'
                    sh 'nohup service tango-db restart'
                    sh 'git checkout user/kmadisa/CB-2672/unit-testing-using-pytango-test-features'
                    sh 'sudo pip install . -U'
                    sh 'python setup.py test'
                } finally {
                    step([$class: 'JUnitResultArchiver', testResults: 'nosetests.xml'])
                }
            }
        }
    }
}
