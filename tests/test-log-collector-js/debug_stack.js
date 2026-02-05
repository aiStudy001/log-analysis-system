/**
 * 스택 트레이스 디버깅
 */

function getStackInfo() {
    const stack = new Error().stack;
    console.log('\n=== Full Stack ===');
    console.log(stack);
    console.log('\n=== Stack Lines ===');
    const stackLines = stack.split('\n');
    stackLines.forEach((line, index) => {
        console.log(`[${index}] ${line}`);
    });
}

function testFunction() {
    console.log('\n=== From testFunction ===');
    getStackInfo();
}

console.log('=== Direct call ===');
getStackInfo();

testFunction();

// 편의 함수를 통한 호출 시뮬레이션
function logWrapper(message) {
    const stack = new Error().stack;
    const stackLines = stack.split('\n');
    console.log('\n=== From logWrapper (simulating logger.info) ===');
    console.log('Caller line [2]:', stackLines[2]);
    console.log('Caller line [3]:', stackLines[3]);

    // Regex 테스트
    const line2 = stackLines[2];
    const line3 = stackLines[3];

    let match2 = line2.match(/at\s+([^\s]+)\s+\(([^:]+):\d+:\d+\)/);
    let match3 = line3.match(/at\s+([^\s]+)\s+\(([^:]+):\d+:\d+\)/);

    console.log('\nMatch [2]:', match2);
    console.log('Match [3]:', match3);
}

function userCode() {
    logWrapper('test message');
}

userCode();
