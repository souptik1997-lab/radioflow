async function loadPatients() {

    const response = await fetch('/api/patients');

    const patients = await response.json();

    console.log(patients);
}

loadPatients();