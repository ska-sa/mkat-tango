pipeline {

    agent {
        label 'camtango_nodb'
    }

    stages {

        stage ('Checkout SCM') {
            steps {
                checkout([
                    $class: 'GitSCM',
                    branches: [[name: "refs/heads/${env.BRANCH_NAME}"]],
                    extensions: [[$class: 'LocalBranch']],
                    userRemoteConfigs: scm.userRemoteConfigs,
                    doGenerateSubmoduleConfigurations: false,
                    submoduleCfg: []
                ])
            }
        }
        stage ('Install & Unit Tests') {
            options {
                timestamps()
                timeout(time: 30, unit: 'MINUTES')
            }
            steps {
                sh 'pip install nose_xunitmp'
                sh 'pip install . -U --pre --user'
                sh 'python setup.py test --with-xunitmp --xunitmp-file nosetests.xml'
            }
            post {
                always {
                    junit 'nosetests.xml'
                    archiveArtifacts 'nosetests.xml'
                }
            }
        }
    }
}
