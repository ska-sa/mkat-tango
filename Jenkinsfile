pipeline {

    agent {
        label 'camtango_nodb_bionic'
    }

    environment {
        KATPACKAGE = "${(env.JOB_NAME - env.JOB_BASE_NAME) - '-multibranch/'}"
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

        stage ('Static analysis') {
            steps {
                sh "pylint ./${KATPACKAGE} --output-format=parseable --exit-zero > pylint.out"
                sh "lint_diff.sh -r ${KATPACKAGE}"
            }

            post {
                always {
                    recordIssues(tool: pyLint(pattern: 'pylint.out'))
                }
            }
        }

        stage ('Install & Unit Tests') {
            options {
                timestamps()
                timeout(time: 30, unit: 'MINUTES')
            }

            steps {
                sh 'pip install coverage==4.5.4 --user'
                sh 'pip install . -U --user'
                sh 'pip install nose_xunitmp --user'
                sh 'python -m coverage run --source="${KATPACKAGE}" -m nose --with-xunitmp --xunitmp-file=nosetests_py27.xml' 
                sh 'python2 -m coverage xml -o coverage_27.xml'
                sh 'python2 -m coverage report -m --skip-covered'
            }

            post {
                always {
                    junit 'nosetests.xml'
                    cobertura coberturaReportFile: 'coverage.xml'
                    archiveArtifacts '*.xml'
                }
            }
        }

        stage('Build & publish packages') {
            when {
                branch 'master'
            }

            steps {
                sh 'fpm -s python -t deb .'
                sh 'python setup.py bdist_wheel'
                sh 'mv *.deb dist/'
                archiveArtifacts 'dist/*'

                // Trigger downstream publish job
                build job: 'ci.publish-artifacts', parameters: [
                        string(name: 'job_name', value: "${env.JOB_NAME}"),
                        string(name: 'build_number', value: "${env.BUILD_NUMBER}")]
            }
        }
    }
}
