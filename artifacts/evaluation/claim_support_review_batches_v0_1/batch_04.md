# Claim-support review batch 04

Allowed labels: `SUPPORTED`, `PARTIALLY_SUPPORTED`, `UNSUPPORTED`, `CONTRADICTED`.

---

## claimrev_046

**Systems:** lora_rag

**Claim:** Cryogenic tank design, manufacturing, insulation, and integration into airframes will be challenging because of the lower cryogenic fuel density, requiring larger tanks for equivalent field length metrics.

**Cited evidence:**

- `C1` | `20250010867:chunk:00003`

methods for ignition sources, ﬂame propagation, and deﬂagration risks diﬀer signiﬁcantly across applications. Other subjects that need to be addressed in combination with the above regulatory challenges are the development of an encompassing aircraft architecture and optimal system integration making the commercial exploitation of a novel aircraft concept viable, as well as the development of relevant safety regulations and certiﬁcation standards for the aircraft and its major components [8]. These studies are focusing on hydrogen turbine engines, fuel cells, electric motors, and hybrid-electric cycles integrated with cryo-fuels using consistent metrics of aircraft eﬃciency and emission improvements. It is important to mature the technologies required in parallel to the aircraft architectures so that the two can feed each other improving the probability of integrated system success. There are numerous technology challenges for aviation with cryogenic fuel storage systems and propulsion including development of cryo-fuel storage and handling, thermal management systems, cryogenic fuel combustion in turbine engines, and next generation scalable engines and fuel cells. Initial challenge includes variabilities in turbine engines and fuel cells considered for integration into commercial aviation propulsion, each with expansive unknowns [9]. Cryogenic tank design, manufacturing, insulation, and integration into airframes will be challenging because of the lower density of the fuel requiring larger tanks for equivalent ﬁeld length metrics [8]. Liquid cryogenic fuels’ maximum handling maximum temperature and density signiﬁcantly diverge from baseline Jet A fuel (kerosene) at 182 °C and 807 kg/m3 with LNH 3 at -36.3 °C and 675 kg/m3, LNG at -160 °C and 424 kg/m3, and LH2 at -253 °C and 71 kg/m3. Although hydrogen oﬀers a much higher gravimetric energy density (LHV ≈ 120 MJ/kg) than jet fuel (LHV ≈ 43 MJ/kg), its low volumetric density requires bulky storage systems, posing substantial integration challenges for long-range, large aircraft. LH2 low temperature,

**Decision:** `SUPPORTED / PARTIALLY_SUPPORTED / UNSUPPORTED / CONTRADICTED`

**Note:**

---

## claimrev_047

**Systems:** lora_rag

**Claim:** The heat exchanger must close at zero flight speed, and at takeoff, the air is relatively hot, making heat transfer difficult.

**Cited evidence:**

- `C1` | `20260003867:chunk:00010`

approaches for MW fuel cell stacks – Lightweight BOP , water and thermal management • Systems Analysis to assess new vehicle configurations Thermal Management System Considerations • Need to reject 40% to 60% of the fuel cell heat energy (~10 MWt) • Need to transition from LT PEM (80C) to HT PEM (200C) to achieve large temperature differential between coolant and airstream during takeoff and climb • Heat rejection must close at zero flight speed, necessitating the placement of the heat exchanger in the propulsor duct • At takeoff, the air is relatively hot, making heat transfer difficult • Potential solution is to include battery power for takeoff and initial climb to reduce heat rejection requirement • Currently working on heat exchanger conceptual design to get initial size and weight Development of cryogenic materials and components evaluation 1. Multiscale model of laminate and ply microstructure – Cool to cryo and evaluate residual stresses per material system 2. NASTRAN/HyperX model of tank – Use HyperX with realistic thermo-mechanical load cases to evaluate optimized designs per material system 3. Progressive damage modeling to model microcracking and permeability – Laminate level or full multiscale FEM – Possibly beyond current resources Use multiscale progressive damage modeling to evaluate novel tank matrix material candidates (i.e. thermoplastics) under realistic thermo- mechanical loading with molecular dynamics data for the neat resin. Manufacturing demonstration of thermoplastic composite tank with new insulation materials. Tank Layup Micro Nano (MD) Commercial Aviation Propulsion Cycles and Utilization: The primary issues unique to aviation propulsion not directly addressed by current commercial transport technologies or NASA space propulsion revolve around the challenging transition of cryo-fuel handling and power/propulsion systems, from space propulsion applications having short lives, very low occupancy to commercial transport applications requiring much longer service lives, much higher occupancy and using high

- `C2` | `20205005005:chunk:00007`

voltage, power, and current. It is also just as important to manage the significant new low-grade heat loads that are introduced each time an electrical component is added to the aircraft (Dooley, 2016); this was a primary consideration in the development of TREES. The challenges with low-grade waste heat in aircraft is five-fold because it  is not useful for work and difficult to reject  adds system mass from large heat exchangers, plumbing, and fluids  reduces net propulsive power from increased drag, compressor bleed, and turbine power extraction  has a limited thermal capacity due to sink temperature or surface availability  increases maintenance due to thermal management system complexity or structural integration challenges Caption: Figure 16.4 Heat sources distributed throughout the aircraft. (a) High-exergy (>20 MW). (b) Low-exergy (<1 MW). Credit: NASA As shown in Figure 16.4, aircraft have a range of heat sources distributed throughout the aircraft. High-exergy waste heat is emitted from the turbofan core, and low-exergy waste heat is distributed nearly everywhere else on the aircraft. The current approaches for managing this heat (Dooley, 2016), along with its drawbacks, are listed in Table 16.2. Table 16.2. Thermal Management Technology Options Thermal management technology Drawback Ram air heat exchanger Adds weight, aircraft drag, displaces fuel capacity Convective skin cooling heat exchanger Adds weight and drag, and requires liquid pumping losses Sinking heat into fuel Limited thermal capacity due to coking and volume Sinking heat into lubricating oil Limited thermal capacity; low T adds heat exchanger mass Active cooling Reduces propulsive efficiency; adds weight and maintenance Phase change cooling Limited thermal capacity; adds weight Heat pipe Does not increase exergy, which impacts mass and efficiency The heat pipe technology is shown as a drawback in Table 16.2 when used in isolation because it does not increase

**Decision:** `SUPPORTED / PARTIALLY_SUPPORTED / UNSUPPORTED / CONTRADICTED`

**Note:**

---

## claimrev_048

**Systems:** base_rag

**Claim:** Battery power is used for takeoff and initial climb to reduce heat rejection requirements.

**Cited evidence:**

- `C1` | `20260003867:chunk:00010`

approaches for MW fuel cell stacks – Lightweight BOP , water and thermal management • Systems Analysis to assess new vehicle configurations Thermal Management System Considerations • Need to reject 40% to 60% of the fuel cell heat energy (~10 MWt) • Need to transition from LT PEM (80C) to HT PEM (200C) to achieve large temperature differential between coolant and airstream during takeoff and climb • Heat rejection must close at zero flight speed, necessitating the placement of the heat exchanger in the propulsor duct • At takeoff, the air is relatively hot, making heat transfer difficult • Potential solution is to include battery power for takeoff and initial climb to reduce heat rejection requirement • Currently working on heat exchanger conceptual design to get initial size and weight Development of cryogenic materials and components evaluation 1. Multiscale model of laminate and ply microstructure – Cool to cryo and evaluate residual stresses per material system 2. NASTRAN/HyperX model of tank – Use HyperX with realistic thermo-mechanical load cases to evaluate optimized designs per material system 3. Progressive damage modeling to model microcracking and permeability – Laminate level or full multiscale FEM – Possibly beyond current resources Use multiscale progressive damage modeling to evaluate novel tank matrix material candidates (i.e. thermoplastics) under realistic thermo- mechanical loading with molecular dynamics data for the neat resin. Manufacturing demonstration of thermoplastic composite tank with new insulation materials. Tank Layup Micro Nano (MD) Commercial Aviation Propulsion Cycles and Utilization: The primary issues unique to aviation propulsion not directly addressed by current commercial transport technologies or NASA space propulsion revolve around the challenging transition of cryo-fuel handling and power/propulsion systems, from space propulsion applications having short lives, very low occupancy to commercial transport applications requiring much longer service lives, much higher occupancy and using high

**Decision:** `SUPPORTED / PARTIALLY_SUPPORTED / UNSUPPORTED / CONTRADICTED`

**Note:**

---

## claimrev_049

**Systems:** lora_rag

**Claim:** Thermal management systems should provide system cooling and heat dissipation, and the thermal management system should be designed to cool the EAP electrical components only.

**Cited evidence:**

- `C1` | `20220005753:chunk:00000`

Health Management Considerations for Electrified Aircraft Propulsion Systems Donald L. Simon NASA Glenn Research Center 21000 Brookpark Road Cleveland, OH, 44135 Presentation to FAA May 4, 2022 1 Electrified Aircraft Propulsion (EAP) EAP Architecture Options • Electrified Aircraft Propulsion relies on the generation, storage, and transmission of electrical power for aircraft propulsion 2 Overview of EAP System Components Generic Hybrid Electric Propulsion System EAP System Components • Supervisory Control: Interface between vehicle and propulsion system. • Gas Turbine Engines: Turbomachinery that converts fuel into thrust and mechanical power. • Gearboxes and Mechanical Drives: Used for transferring mechanical power throughout EAP system. • Electric Machines: Generators and motors. Used for converting mechanical power into electricity or vice versa. • Power Electronics and Power Distribution Systems: Handles switching, power conversion, and transmission of electrical power throughout system. • Energy Storage Systems: Systems for the storage of electrical energy such as batteries and supercapacitors. • Propulsors: Motor driven propellers or fans used to generate thrust. • Thermal Management Systems: Provide system cooling and heat dissipation X Turboshaft Engine Electric Generator Electronic Engine Control Thrust Demand, Phase of FlightIntegrated Supervisory Control System Thermal Management System Motor Control Unit Inverter DC Power Bus Electric Motor Propulsor Battery System BMS + Battery - “Electric Engine” Generator Control Unit Rectifier X Gearbox Gearbox Supervisory Control 3 EAP Subsystem Degradation, Faults, Failure Modes, and Effects • EAP degradation, faults, and failure modes present new health management challenges … • Requires background understanding of: ▪ Electrical engineering ▪ Electrical system control and concept of operations (motor control, generator control, battery management systems) • Requires new sensor measurement types ▪ Current, voltage • Electrical systems don’t always degrade/fail gracefully ▪ Makes early (timely) diagnosis to enable maintenance challenging 4 EAP Subsystem Degradation, Faults, Failure Modes, and Effects (cont.) Gas Turbine

- `C2` | `20220004260:chunk:00000`

Health Management Considerations for Electrified Aircraft Propulsion Systems Donald L. Simon NASA Glenn Research Center 21000 Brookpark Road Cleveland, OH, 44135 SAE E32 Aerospace Propulsion Health Management Committee Meeting March 29-31, 2022 Hybrid meeting (in-person Madrid, Spain and virtual) 1 Electrified Aircraft Propulsion (EAP) EAP Architecture Options • Electrified Aircraft Propulsion relies on the generation, storage, and transmission of electrical power for aircraft propulsion 2 Overview of EAP System Components Generic Hybrid Electric Propulsion System EAP System Components • Supervisory Control: Interface between vehicle and propulsion system. • Gas Turbine Engines: Turbomachinery that converts fuel into thrust and mechanical power. • Gearboxes and Mechanical Drives: Used for transferring mechanical power throughout EAP system. • Electric Machines: Generators and motors. Used for converting mechanical power into electricity or vice versa. • Power Electronics and Power Distribution Systems: Handles switching, power conversion, and transmission of electrical power throughout system. • Energy Storage Systems: Systems for the storage of electrical energy such as batteries and supercapacitors. • Propulsors: Motor driven propellers or fans used to generate thrust. • Thermal Management Systems: Provide system cooling and heat dissipation X Turboshaft Engine Electric Generator Electronic Engine Control Thrust Demand, Phase of FlightIntegrated Supervisory Control System Thermal Management System Motor Control Unit Inverter DC Power Bus Electric Motor Propulsor Battery System BMS + Battery - “Electric Engine” Generator Control Unit Rectifier X Gearbox Gearbox Supervisory Control 3 EAP Subsystem Degradation, Faults, Failure Modes, and Effects • EAP degradation, faults, and failure modes present new health management challenges … • Requires background understanding of: ▪ Electrical engineering ▪ Electrical system control and concept of operations (motor control, generator control, battery management systems) • Requires new sensor measurement types ▪ Current, voltage • Electrical systems don’t always degrade/fail gracefully ▪ Makes early (timely) diagnosis to enable maintenance challenging

**Decision:** `SUPPORTED / PARTIALLY_SUPPORTED / UNSUPPORTED / CONTRADICTED`

**Note:**

---

## claimrev_050

**Systems:** base_rag

**Claim:** The low volumetric density of cryogenic hydrogen requires larger tanks for equivalent field length metrics, posing significant integration challenges.

**Cited evidence:**

- `C1` | `20250010867:chunk:00003`

methods for ignition sources, ﬂame propagation, and deﬂagration risks diﬀer signiﬁcantly across applications. Other subjects that need to be addressed in combination with the above regulatory challenges are the development of an encompassing aircraft architecture and optimal system integration making the commercial exploitation of a novel aircraft concept viable, as well as the development of relevant safety regulations and certiﬁcation standards for the aircraft and its major components [8]. These studies are focusing on hydrogen turbine engines, fuel cells, electric motors, and hybrid-electric cycles integrated with cryo-fuels using consistent metrics of aircraft eﬃciency and emission improvements. It is important to mature the technologies required in parallel to the aircraft architectures so that the two can feed each other improving the probability of integrated system success. There are numerous technology challenges for aviation with cryogenic fuel storage systems and propulsion including development of cryo-fuel storage and handling, thermal management systems, cryogenic fuel combustion in turbine engines, and next generation scalable engines and fuel cells. Initial challenge includes variabilities in turbine engines and fuel cells considered for integration into commercial aviation propulsion, each with expansive unknowns [9]. Cryogenic tank design, manufacturing, insulation, and integration into airframes will be challenging because of the lower density of the fuel requiring larger tanks for equivalent ﬁeld length metrics [8]. Liquid cryogenic fuels’ maximum handling maximum temperature and density signiﬁcantly diverge from baseline Jet A fuel (kerosene) at 182 °C and 807 kg/m3 with LNH 3 at -36.3 °C and 675 kg/m3, LNG at -160 °C and 424 kg/m3, and LH2 at -253 °C and 71 kg/m3. Although hydrogen oﬀers a much higher gravimetric energy density (LHV ≈ 120 MJ/kg) than jet fuel (LHV ≈ 43 MJ/kg), its low volumetric density requires bulky storage systems, posing substantial integration challenges for long-range, large aircraft. LH2 low temperature,

**Decision:** `SUPPORTED / PARTIALLY_SUPPORTED / UNSUPPORTED / CONTRADICTED`

**Note:**

---

## claimrev_051

**Systems:** base_rag

**Claim:** Aircraft battery systems are cooled using active cooling methods such as forced convection of ambient air through the battery pack, which is optimized using conjugate heat transfer (CHT) techniques.

**Cited evidence:**

- `C1` | `20180004867:chunk:00003`

management would likely be required, the battery p acks and most power electronics were placed in the main body of the aircraft . This could make battery replacement easier, as well as facilitate design and substitution of the all -battery system with a hybrid system using genset (fueled engine + generator) using energy-dense hydrocarbon fuels. This would also facilitate employing more-highly integrated cryogenic cooled systems that offer other benefits. The added weight of the hybrid system could be offset by reducing the battery size and capability. Figure 2. Notional VTOL vehicle layout. Figure 3 shows the simple mission profile used to size the baseline all -electric, battery aircraft wit h range set to 150 nautical miles, flying at best range velocity V br. To simulate shorter UAM operations, we assumed repeated mission profiles flying V br at 20 or 50 nautical mile range, which would minimize total energy used. Figure 3. Mission Profile for sizing, maximum range or UAM missions. PROPULSION AND ENERGY CONCEPTS Propulsion and energy characteristics used to develop the vehicle characteristics reported here are shown in Table 1, further details can be found in References 1 and 4. Performance levels believed achievable in 15 years were used for this effort. Impressive improvements in electric motor efficiency and power to weight offer an opportunity for new and more capable aviation vehicles. However, widespread adoption of all electric systems is still hampered by the much lower electrical energy density for batteries versus hydrocarbon fuels. This is true even when including the much lower efficiencies of the heat engines employing hydrocarbon fuels. Table 1. Motive engine and energy storage characteristics (15 year technologies). Engine type Power / weight, hp/lb. (kW/kg) η, % Fuel energy density, MJ/kg (Wh/kg) Net energy density, MJ/kg (Wh/kg) all-electric, battery* 3.4 (5.6) 93 1.75 (486) 1.63

**Decision:** `SUPPORTED / PARTIALLY_SUPPORTED / UNSUPPORTED / CONTRADICTED`

**Note:**

---

## claimrev_052

**Systems:** lora_rag

**Claim:** Active cooling approaches include passive and active methods. Passive cooling requires additional pumps or power and increases the battery pack's weight by using a larger surface area for heat rejection.

**Cited evidence:**

- `C1` | `20240014672:chunk:00001`

cooling pump power and battery weight, respectively, and the maximal temperature constraint is satisfied. This work has the potential to reduce battery-pack weight, improve performance, and reduce the weight of thermal management systems for electric vertical take-off and landing aircraft. I. Introduction Thermal management is essential for battery packs in electric aircraft, which lack the natural heat dissipation of conventional air-breathing engines [1]. Accumulated heat can damage batteries and other components, compromising the safety and performance of the aircraft. There are two primary methods for cooling the battery: passive and active. Passive cooling has the advantage of not requiring additional pumps or power, but it typically requires a greater surface area dedicated to heat rejection to the external environment, thereby increasing the overall weight of the battery pack. In contrast, active cooling can significantly reduce the battery pack weight, but it requires an efficient cooling system design to offset the added weight and power of the cooling pump [2]. Because ambient air is a readily available resource for aircraft, this paper considers an active cooling concept with forced convection of ambient air through the battery pack. Conjugate heat transfer (CHT) optimization is a powerful approach to designing high-performance active cooling battery packs. It enables more realistic aero-thermal coupling by integrating computational fluid dynamics (CFD) to simulate fluid domains and conduction heat transfer solvers for the solid domains. The CHT optimization method has been used to analyze the aerodynamics and heat transfer of various battery pack shapes and flow conditions [3, 4]. CHT-based design optimization studies have also been conducted to improve ∗Assistant Professor, Department of Aerospace Engineering, AIAA Senior Member. Email: phe@iastate.edu †PhD Student, Department of Aerospace Engineering, AIAA Student Member. ‡PhD Student, Department of Aerospace Engineering, AIAA Student Member. §Research Engineer, Propulsion Systems Analysis Branch, AIAA Member. 1 performance[5];however,inthisstudy,agradient-freeoptimizationalgorithmwasused.

- `C2` | `20240014672:chunk:00000`

Aerothermal Shape Optimization of Actively-Cooled Battery Packs using Conjugate Heat Transfer Ping He∗, Christian A. Psenica†, and Lean Fang‡ Iowa State University, Ames, IA 50011 Mark K. Leader§ NASA Glenn Research Center, Cleveland, OH 44135 Thermal management for batteries is important for electric aircraft because battery temperature is critically important to vehicle safety, and it also has a direct impact on the efficiency of the battery system. Because ambient air is a readily available resource for aircraft, this paper considers an active cooling concept with forced convection of ambient air through the battery pack. Conjugate heat transfer analysis is used to solve the coupled aero-thermal problem, which consists of a finite-volume computational fluid dynamics solver for the fluid domain, and a conduction heat transfer solver for the solid domain. A mixed Neumann and Dirichlet boundary condition is developed for the fluid-solid interface, which allows the solid domain to completely submerge in the fluid domain. A gradient-based optimization method is adopted, and the discrete adjoint approach implemented in DAFoam is used to efficiently compute the gradients. The aero-thermal coupling for primal analysis and gradient computation is handled using the OpenMDAO-based MPhys framework. A constant heat source is prescribed for the battery cells, and the battery shape (design variable) is optimized to minimize cooling pump power and battery weight (composite objective function) while keeping the battery temperature below a threshold (constraint). The optimized design achieves a 44.6% and 1.5% reduction in the cooling pump power and battery weight, respectively, and the maximal temperature constraint is satisfied. This work has the potential to reduce battery-pack weight, improve performance, and reduce the weight of thermal management systems for electric vertical take-off and landing aircraft. I. Introduction Thermal management is essential for battery packs in electric aircraft, which lack the natural heat dissipation of conventional

**Decision:** `SUPPORTED / PARTIALLY_SUPPORTED / UNSUPPORTED / CONTRADICTED`

**Note:**

---

## claimrev_053

**Systems:** lora_rag

**Claim:** Electric propulsion is capable of achieving equivalent system-weight-to-performance ratios, and its latent value includes dramatic reductions in total energy used because of the high conversion efficiency from electricity to shaft power, which translates to dramatic reductions in emissions, as well as many other fundamentally new and improved characteristics.

**Cited evidence:**

- `C2` | `20140011913:chunk:00011`

energy constrained, what new aircraft types and architectures do the different characteristics enable, what evaluation metrics should be used in their comparisons, and how could electric aircraft evolve to eventually replace reciprocating and even turbine aircraft?” These are the questions that were asked in the NASA Zip Aviation studies that investigated the enabling characteristics of autonomy and distributed electric propulsion technologies towards the On-Demand Aviation emergent market needs. The results of that study indicated that even at a mere 400 Whr/kg advanced electric GA aircraft are not only competitive to reciprocating aircraft, but that they achieve 2 to 8 time factor improvements across metrics of comparison including cost, safety, community noise, propulsion component reliability, and efficiency. The Zip study indicates that research investment can yield far better products than State Of the Art (SOA) GA aircraft in less than 10 years across key future societal metrics of interest, and predicts the rapid implementation of electric propulsion to the GA market (as well as newly enabled markets). Figure 1: Comparative characteristics of electric propulsion to reciprocating or turbine engines for use in initial Unmanned Aerial System (UAS) or GA market small aircraft mission applications. American Institute of Aeronautics and Astronautics 5 If the criteria of achieving equivalent comparable propulsi on system weight to performance is used for electric propulsion, and batteries continue to improve their energy density at ~8% per year, it’ll take 30 years before they achieve a 10x improvement and parity for this metric. Electric propulsion versus reciprocating or turbine propulsion systems shouldn’t be compared merely through legacy metrics that don’t include other important characteristics of future interest, which could provide impor tant latent value. Latent value in terms of electric propulsion system includes dramatic reductions in the total energy used because of the high conversion efficiency from electricity

**Decision:** `SUPPORTED / PARTIALLY_SUPPORTED / UNSUPPORTED / CONTRADICTED`

**Note:**

---

## claimrev_054

**Systems:** lora_rag

**Claim:** The desire to distribute propulsion is also encouraged by the compactness of electric motors.

**Cited evidence:**

- `C1` | `20140011913:chunk:00013`

in the past propulsion technologies have been responsible for the most spectacular aviation advances, because propulsion technology sensitivities are so high in comparison to other disciplines. Likewise, electric propulsion sensitivities demonstrate opportunity for incredible advances, far more than in any other discipline. Because of this potential to achieve such breakthrough changes, and because (like flash drives compared to magnetic drives) electric propulsion offers new latent benefits while relatively poor legacy metric characteristics, elec tric propulsion is considered to be a classic disruptive technology that has the potential to quickly displace conven tional propulsion technologies; but in ways that will likely be perceived as unexpected (but with comparison to other disruptive technologies, are actually quite predictable). II. Misconception 1: The Design of Electric Aircraft is No Different than Existing Aircraft Because electric propulsion is a relatively scale independent technology, the ability to distribute the propulsion system across the airframe to achieve integration advantages is penalty-free, or in many instances, offers substantial benefits. Scale independence is considered to mean that whether electric motors and controllers are distributed to motors of 1 hp, 10 hp, or 100 hp; their power to weight and efficiency are essentially the same. As electric propulsion is pushed into larg er and larger aircraft applications, th is trend may extend to far larger motor sizes as well. The desire to distribute the propulsion is also encouraged by the compactness of electric motors. Scale independence is not a characteristic of reciprocatin g or turbine engines which suffer significant penalties as they are scaled down in size, with the power to weight, efficiency, and reliability suffering dramatically. These are not merely a matter of engine development focusing research dollars on large engines, but fundamental physics including volume to surface area ratios, Reynolds numbers, and tolerances required and achievable in manufacturing.

**Decision:** `SUPPORTED / PARTIALLY_SUPPORTED / UNSUPPORTED / CONTRADICTED`

**Note:**

---

## claimrev_055

**Systems:** lora_rag

**Claim:** Integrated Fault and Thermal Management systems will be based on the variety of configurations shown in Figure 16.6, but they all have in common the need to protect against electrical faults with DC breakers and manage the waste heat produced by everything shown.

**Cited evidence:**

- `C1` | `20205005005:chunk:00009`

of transport-class electrification can be nullified. Moreover, even an ideally 99%-efficient component will often be required to operate outside its peak performance zone, and this can result in a thermal runaway scenario unless active thermal control features are available to mitigate this response. It is therefore critically important to integrate an active thermal control system, such as TREES, with all the systems on the aircraft. Integrated Fault and Thermal Management Future electric aircraft propulsion systems will be based on the variety of configurations shown in Figure 16.6. Still, they all have in common the need to protect against electrical faults with DC breakers (indicated by the yellow dots) and to manage the waste heat produced by everything shown. Caption: Figure 16.6. Powertrain configurations require both thermal and fault management protection (yellow dots). (a) Parallel hybrid. (b) Turboelectric. (c) Series hybrid. (d) All electric. Credit: NASA Figure 16.7 depicts the TREES thermal management system (Dyson, 2019) integrated with a fault management system and applied to a Boeing 737 flight vehicle with parallel hybrid propulsion. The basic approach here is to extract high-exergy waste heat from the turbofan core using low–mass, SiC-coated graphite heat exchangers to thermoacoustically generate a ducted acoustic wave that is used to deliver mechanical energy throughout the aircraft. This acoustic energy can then operate a thermoacoustic heat pump to actively refrigerate the powertrain components while collecting the low- exergy waste heat from the powertrain and convert it to high-exergy useful heat, through which dynamically switchable heat pipes can then deliver throughout the aircraft for the beneficial applications shown in Table 16.3. Caption: Figure 16.7. TREES uses thermoacoustic and dynamically redirectable heat pipe tubes embedded in the aircraft to recycle both the turbofan and powertrain waste heat Credit: NASA Table 16.3. Beneficial Applications of Higher Exergy Waste Heat from

**Decision:** `SUPPORTED / PARTIALLY_SUPPORTED / UNSUPPORTED / CONTRADICTED`

**Note:**

---

## claimrev_056

**Systems:** lora_rag

**Claim:** Electric propulsion can be scaled to larger motor sizes as well.

**Cited evidence:**

- `C1` | `20140011913:chunk:00013`

in the past propulsion technologies have been responsible for the most spectacular aviation advances, because propulsion technology sensitivities are so high in comparison to other disciplines. Likewise, electric propulsion sensitivities demonstrate opportunity for incredible advances, far more than in any other discipline. Because of this potential to achieve such breakthrough changes, and because (like flash drives compared to magnetic drives) electric propulsion offers new latent benefits while relatively poor legacy metric characteristics, elec tric propulsion is considered to be a classic disruptive technology that has the potential to quickly displace conven tional propulsion technologies; but in ways that will likely be perceived as unexpected (but with comparison to other disruptive technologies, are actually quite predictable). II. Misconception 1: The Design of Electric Aircraft is No Different than Existing Aircraft Because electric propulsion is a relatively scale independent technology, the ability to distribute the propulsion system across the airframe to achieve integration advantages is penalty-free, or in many instances, offers substantial benefits. Scale independence is considered to mean that whether electric motors and controllers are distributed to motors of 1 hp, 10 hp, or 100 hp; their power to weight and efficiency are essentially the same. As electric propulsion is pushed into larg er and larger aircraft applications, th is trend may extend to far larger motor sizes as well. The desire to distribute the propulsion is also encouraged by the compactness of electric motors. Scale independence is not a characteristic of reciprocatin g or turbine engines which suffer significant penalties as they are scaled down in size, with the power to weight, efficiency, and reliability suffering dramatically. These are not merely a matter of engine development focusing research dollars on large engines, but fundamental physics including volume to surface area ratios, Reynolds numbers, and tolerances required and achievable in manufacturing.

**Decision:** `SUPPORTED / PARTIALLY_SUPPORTED / UNSUPPORTED / CONTRADICTED`

**Note:**

---

## claimrev_057

**Systems:** lora_rag

**Claim:** Battery-electric aircraft produce large amounts of low-grade waste heat and require large, heavy thermal-management systems that cause drag.

**Cited evidence:**

- `C1` | `20205004497:chunk:00013`

a result of increased thermal management system power draw. The wattage consumed by the coolant loop is considered an eﬃciency loss on the drive-train, and the lighter vehicle saves substantial weight on the battery at the cost of requiring higher power cooling. Additional proﬁles are included in the appendix for the six-passenger vehicle variant. Fig. 8 Drive-train Eﬃciency Proﬁle over Optimized Trajectories Across Multiple Energy Densities 9 V. Conclusions and Future Work This paper examined mission-dependent battery waste heat starting with a notional X-57 mission. Performance impacts from battery size and energy density were quantiﬁed for a statically sized, ﬁxed-wing vehicle. Next, a VTOL quadrotor was optimally sized for various ranges and achievable energy density. The variation in sensitivity between each of these missions highlights the need for openly available surrogate models to give battery system engineers more realistic benchmarks for designing batteries. Additional real-world constraints like volume and degradation are not evaluated explicitly but can be posed as additional weight penalty margins, if they exceed certain thresholds. This paper shows the energy and thermal sizing impacts for a speciﬁc Li-ion battery chemistry. Future work will attempt to create chemistry agnostic sensitivity functions with weight and thermal loads as the input and power proﬁles as the output. Follow-on studies are currently being conducted to better determine pack weight knockdowns based on the magnitude of the waste heat and the size of the thermal system. As new electric VTOL conﬁgurations are developed, understanding realistic energy density and eﬃciency values will be critical for creating optimally sized vehicles. Ideally, these results help assist in scoping the magnitude of the battery design challenge and can be used to help set productive benchmarks. Appendix Regressions on each swept design variable are provided in the following section: Energy Density is ﬁxed as 400 Wh/kg for

- `C2` | `20240014672:chunk:00001`

cooling pump power and battery weight, respectively, and the maximal temperature constraint is satisfied. This work has the potential to reduce battery-pack weight, improve performance, and reduce the weight of thermal management systems for electric vertical take-off and landing aircraft. I. Introduction Thermal management is essential for battery packs in electric aircraft, which lack the natural heat dissipation of conventional air-breathing engines [1]. Accumulated heat can damage batteries and other components, compromising the safety and performance of the aircraft. There are two primary methods for cooling the battery: passive and active. Passive cooling has the advantage of not requiring additional pumps or power, but it typically requires a greater surface area dedicated to heat rejection to the external environment, thereby increasing the overall weight of the battery pack. In contrast, active cooling can significantly reduce the battery pack weight, but it requires an efficient cooling system design to offset the added weight and power of the cooling pump [2]. Because ambient air is a readily available resource for aircraft, this paper considers an active cooling concept with forced convection of ambient air through the battery pack. Conjugate heat transfer (CHT) optimization is a powerful approach to designing high-performance active cooling battery packs. It enables more realistic aero-thermal coupling by integrating computational fluid dynamics (CFD) to simulate fluid domains and conduction heat transfer solvers for the solid domains. The CHT optimization method has been used to analyze the aerodynamics and heat transfer of various battery pack shapes and flow conditions [3, 4]. CHT-based design optimization studies have also been conducted to improve ∗Assistant Professor, Department of Aerospace Engineering, AIAA Senior Member. Email: phe@iastate.edu †PhD Student, Department of Aerospace Engineering, AIAA Student Member. ‡PhD Student, Department of Aerospace Engineering, AIAA Student Member. §Research Engineer, Propulsion Systems Analysis Branch, AIAA Member. 1 performance[5];however,inthisstudy,agradient-freeoptimizationalgorithmwasused.

**Decision:** `SUPPORTED / PARTIALLY_SUPPORTED / UNSUPPORTED / CONTRADICTED`

**Note:**

---

## claimrev_058

**Systems:** base_rag

**Claim:** E1

**Cited evidence:**

- `C1` | `20220005753:chunk:00000`

Health Management Considerations for Electrified Aircraft Propulsion Systems Donald L. Simon NASA Glenn Research Center 21000 Brookpark Road Cleveland, OH, 44135 Presentation to FAA May 4, 2022 1 Electrified Aircraft Propulsion (EAP) EAP Architecture Options • Electrified Aircraft Propulsion relies on the generation, storage, and transmission of electrical power for aircraft propulsion 2 Overview of EAP System Components Generic Hybrid Electric Propulsion System EAP System Components • Supervisory Control: Interface between vehicle and propulsion system. • Gas Turbine Engines: Turbomachinery that converts fuel into thrust and mechanical power. • Gearboxes and Mechanical Drives: Used for transferring mechanical power throughout EAP system. • Electric Machines: Generators and motors. Used for converting mechanical power into electricity or vice versa. • Power Electronics and Power Distribution Systems: Handles switching, power conversion, and transmission of electrical power throughout system. • Energy Storage Systems: Systems for the storage of electrical energy such as batteries and supercapacitors. • Propulsors: Motor driven propellers or fans used to generate thrust. • Thermal Management Systems: Provide system cooling and heat dissipation X Turboshaft Engine Electric Generator Electronic Engine Control Thrust Demand, Phase of FlightIntegrated Supervisory Control System Thermal Management System Motor Control Unit Inverter DC Power Bus Electric Motor Propulsor Battery System BMS + Battery - “Electric Engine” Generator Control Unit Rectifier X Gearbox Gearbox Supervisory Control 3 EAP Subsystem Degradation, Faults, Failure Modes, and Effects • EAP degradation, faults, and failure modes present new health management challenges … • Requires background understanding of: ▪ Electrical engineering ▪ Electrical system control and concept of operations (motor control, generator control, battery management systems) • Requires new sensor measurement types ▪ Current, voltage • Electrical systems don’t always degrade/fail gracefully ▪ Makes early (timely) diagnosis to enable maintenance challenging 4 EAP Subsystem Degradation, Faults, Failure Modes, and Effects (cont.) Gas Turbine

**Decision:** `SUPPORTED / PARTIALLY_SUPPORTED / UNSUPPORTED / CONTRADICTED`

**Note:**

---

## claimrev_059

**Systems:** lora_rag

**Claim:** Electric propulsion is distinguished by its ability to distribute propulsion systems across the airframe, enabling integration advantages and compactness. Scale independence is considered to mean that whether electric motors and controllers are distributed to motors of 1 hp, 10 hp, or 100 hp, their power-to-weight and efficiency are essentially the same.

**Cited evidence:**

- `C1` | `20140011913:chunk:00013`

in the past propulsion technologies have been responsible for the most spectacular aviation advances, because propulsion technology sensitivities are so high in comparison to other disciplines. Likewise, electric propulsion sensitivities demonstrate opportunity for incredible advances, far more than in any other discipline. Because of this potential to achieve such breakthrough changes, and because (like flash drives compared to magnetic drives) electric propulsion offers new latent benefits while relatively poor legacy metric characteristics, elec tric propulsion is considered to be a classic disruptive technology that has the potential to quickly displace conven tional propulsion technologies; but in ways that will likely be perceived as unexpected (but with comparison to other disruptive technologies, are actually quite predictable). II. Misconception 1: The Design of Electric Aircraft is No Different than Existing Aircraft Because electric propulsion is a relatively scale independent technology, the ability to distribute the propulsion system across the airframe to achieve integration advantages is penalty-free, or in many instances, offers substantial benefits. Scale independence is considered to mean that whether electric motors and controllers are distributed to motors of 1 hp, 10 hp, or 100 hp; their power to weight and efficiency are essentially the same. As electric propulsion is pushed into larg er and larger aircraft applications, th is trend may extend to far larger motor sizes as well. The desire to distribute the propulsion is also encouraged by the compactness of electric motors. Scale independence is not a characteristic of reciprocatin g or turbine engines which suffer significant penalties as they are scaled down in size, with the power to weight, efficiency, and reliability suffering dramatically. These are not merely a matter of engine development focusing research dollars on large engines, but fundamental physics including volume to surface area ratios, Reynolds numbers, and tolerances required and achievable in manufacturing.

**Decision:** `SUPPORTED / PARTIALLY_SUPPORTED / UNSUPPORTED / CONTRADICTED`

**Note:**

---

## claimrev_060

**Systems:** base_rag

**Claim:** Electric propulsion systems can achieve significant improvements in performance metrics such as cost, safety, and emissions.

**Cited evidence:**

- `C2` | `20140011913:chunk:00011`

energy constrained, what new aircraft types and architectures do the different characteristics enable, what evaluation metrics should be used in their comparisons, and how could electric aircraft evolve to eventually replace reciprocating and even turbine aircraft?” These are the questions that were asked in the NASA Zip Aviation studies that investigated the enabling characteristics of autonomy and distributed electric propulsion technologies towards the On-Demand Aviation emergent market needs. The results of that study indicated that even at a mere 400 Whr/kg advanced electric GA aircraft are not only competitive to reciprocating aircraft, but that they achieve 2 to 8 time factor improvements across metrics of comparison including cost, safety, community noise, propulsion component reliability, and efficiency. The Zip study indicates that research investment can yield far better products than State Of the Art (SOA) GA aircraft in less than 10 years across key future societal metrics of interest, and predicts the rapid implementation of electric propulsion to the GA market (as well as newly enabled markets). Figure 1: Comparative characteristics of electric propulsion to reciprocating or turbine engines for use in initial Unmanned Aerial System (UAS) or GA market small aircraft mission applications. American Institute of Aeronautics and Astronautics 5 If the criteria of achieving equivalent comparable propulsi on system weight to performance is used for electric propulsion, and batteries continue to improve their energy density at ~8% per year, it’ll take 30 years before they achieve a 10x improvement and parity for this metric. Electric propulsion versus reciprocating or turbine propulsion systems shouldn’t be compared merely through legacy metrics that don’t include other important characteristics of future interest, which could provide impor tant latent value. Latent value in terms of electric propulsion system includes dramatic reductions in the total energy used because of the high conversion efficiency from electricity

**Decision:** `SUPPORTED / PARTIALLY_SUPPORTED / UNSUPPORTED / CONTRADICTED`

**Note:**

